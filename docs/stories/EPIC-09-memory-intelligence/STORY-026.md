# STORY-026: Conversational Memory Chat — Backend

**Epic:** EPIC-09 — Memory Intelligence
**Priority:** P0
**Complexity:** Large
**Depends on:** STORY-015 (hybrid retrieval service must exist)

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory — especially RULE 2 tenant isolation, RULE 6 lazy imports)
> 2. `docs/architecture/03-api-contract.md` — existing endpoints to understand naming conventions
> 3. `docs/architecture/02-database-schema.md` — existing models; new `chat_sessions` table follows same conventions
> 4. `docs/architecture/04-background-jobs.md` — SSE streaming pattern (chat uses direct SSE, NOT ARQ)
> 5. `docs/stories/EPIC-05-metadoc/STORY-015.md` — RAGService.retrieve() that this story reuses

---

## User Story
As a user, I want to ask my knowledge base questions in a conversational dialogue
so that I can explore my memory interactively without generating a full document every time.

## Context
- Retrieval: reuse `RAGService.retrieve()` from STORY-015 — same hybrid Qdrant + Neo4j retrieval
- Streaming: direct SSE from route handler (NOT through ARQ queue — chat must feel instant)
- Sessions: multi-turn conversation stored in PostgreSQL `chat_sessions` table
- Credits: cheaper than Meta-Doc (shorter context, smaller model preferred for speed)
- Key distinction from Meta-Doc: chat is conversational (back-and-forth), not document synthesis

## Acceptance Criteria
- [ ] AC-1: `POST /v1/chat/message` accepts `{message, session_id?, profile_id, model}` and streams `text/event-stream`
- [ ] AC-2: First token arrives at client within 3 seconds (retrieval + LLM start)
- [ ] AC-3: Response includes citations: final SSE event `{type: "done", citations: [{memory_id, content_preview, source_filename}]}`
- [ ] AC-4: `GET /v1/chat/sessions` returns paginated list of past sessions for current user (newest first)
- [ ] AC-5: `GET /v1/chat/sessions/{session_id}` returns full session with all messages
- [ ] AC-6: `DELETE /v1/chat/sessions/{session_id}` deletes session (tenant-scoped — user can only delete own sessions)
- [ ] AC-7: Multi-turn context: last 6 messages from session passed to LLM as conversation history
- [ ] AC-8: Credit deduction: 3 credits (Haiku) or 8 credits (Sonnet) per message, checked before streaming starts
- [ ] AC-9: `402` returned if insufficient credits — before any retrieval or LLM call
- [ ] AC-10: Tenant isolation: Qdrant retrieval always filtered by tenant_id; session queries always scoped by user_id
- [ ] AC-11: Session auto-created on first message if no `session_id` provided; `session_id` returned in first SSE event

## Technical Notes

### New PostgreSQL Table: `chat_sessions`

```python
# src/models/chat_session.py
import uuid
from datetime import datetime, UTC
from typing import Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON

class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: uuid.UUID | None = Field(default=None, foreign_key="system_profiles.id")
    title: str | None = None               # auto-generated from first message (first 60 chars)
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON),
    )
    # messages format: [{role: "user"|"assistant", content: str, created_at: ISO8601}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### Files to Create
- `src/models/chat_session.py` — ChatSession SQLModel
- `src/api/routes/chat.py` — all chat endpoints
- `src/schemas/chat.py` — ChatMessageRequest, ChatSessionResponse, CitationItem
- `src/services/chat_service.py` — orchestrates retrieval + LLM + session persistence
- `alembic/versions/XXX_add_chat_sessions.py` — Alembic migration
- `tests/integration/api/test_chat_endpoints.py`

### Files to Modify
- `src/api/main.py` — include chat router
- `src/workers/main.py` — no change (chat does NOT use ARQ)

### Architecture Constraints
- Chat uses **direct SSE streaming** from the route handler — NOT queued through ARQ
  - Reason: conversational UX requires < 3s to first token; queue adds latency
  - ARQ is for long-running background work (ingestion, meta-doc synthesis)
  - Chat retrieval + LLM streaming is interactive and completes in < 30s
- Use `asyncio.timeout(60)` inside the streaming generator — close connection on timeout
- The `anthropic` import MUST be inside the function body (`# noqa: PLC0415`)
- Qdrant search MUST include `tenant_id` filter (RULE 2 — never skip this)
- Session `messages` column uses JSON (not JSONB) — PostgreSQL JSON is sufficient here
- Only the last 6 messages sent to LLM as context (prevent prompt bloat)
- `session_id` returned in the FIRST SSE event so client can store it for multi-turn
- Model resolution order: request body `model` → user's `preferred_model` → Haiku default
- Map aliases before Anthropic call: `"haiku"` → `"claude-haiku-4-5-20251001"`,
  `"sonnet"` → `"claude-sonnet-4-6"`
- Credit cost: 3 credits (Haiku), 8 credits (Sonnet) — checked before retrieval

### Chat Streaming Pattern (direct SSE, no ARQ)

```python
# src/api/routes/chat.py
from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter, Depends, Request
import asyncio, json

router = APIRouter(prefix="/v1/chat", tags=["chat"])

@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    http_request: Request,
    user: dict = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    # 1. Credit check FIRST (before any expensive work)
    credits_needed = 3 if request.model == "haiku" else 8
    await credit_service.check_or_raise(user["user_id"], credits_needed, db)

    # 2. Get or create session
    session = await chat_service.get_or_create_session(
        user_id=user["user_id"],
        session_id=request.session_id,
        profile_id=request.profile_id,
        first_message=request.message,
        db=db,
    )

    async def event_generator():
        # Yield session_id immediately so client can track multi-turn
        yield {"data": json.dumps({"type": "session", "session_id": str(session.id)})}

        # 3. Retrieve relevant context (hybrid Qdrant + Neo4j)
        chunks = await rag_service.retrieve(
            prompt=request.message,
            profile_id=request.profile_id,
            tenant_id=user["user_id"],
            limit=8,  # fewer chunks than Meta-Doc — chat is more focused
        )

        # 4. Build conversation messages (last 6 turns + new message)
        history = chat_service.build_history(session.messages[-6:])

        # 5. Stream LLM response
        from anthropic import AsyncAnthropic  # noqa: PLC0415
        client = AsyncAnthropic()
        full_response = ""

        try:
            async with asyncio.timeout(60):
                async with client.messages.stream(
                    model="claude-haiku-4-5-20251001" if request.model == "haiku" else "claude-sonnet-4-6",
                    max_tokens=2048,
                    system=chat_service.build_system_prompt(chunks),
                    messages=history + [{"role": "user", "content": request.message}],
                ) as stream:
                    async for text in stream.text_stream:
                        full_response += text
                        yield {"data": json.dumps({"type": "token", "content": text})}
        except asyncio.TimeoutError:
            yield {"data": json.dumps({"type": "error", "message": "Response timed out"})}
            return

        # 6. Save message + response to session; deduct credits
        citations = chat_service.extract_citations(chunks)
        await chat_service.save_turn(session.id, request.message, full_response, db)
        await credit_service.deduct(user["user_id"], credits_needed, "chat_message", db)

        yield {"data": json.dumps({
            "type": "done",
            "citations": citations,
            "credits_consumed": credits_needed,
        })}

    return EventSourceResponse(event_generator())
```

### System Prompt Pattern

```python
# src/services/chat_service.py
def build_system_prompt(self, chunks: list[RetrievedChunk]) -> str:
    context_block = "\n\n".join([
        f"[Memory {i+1} — from {c.source_filename}]:\n{c.content}"
        for i, c in enumerate(chunks)
    ])
    return f"""You are Ravenbase, an AI assistant with access to the user's personal
knowledge base. Answer questions based ONLY on the provided memories below.

If the answer is not in the provided memories, say so explicitly.
Be conversational, direct, and concise. When referencing specific memories,
mention the source (e.g., "According to your notes from resume_2023.pdf...").

USER'S MEMORIES:
{context_block}
"""
```

### Credit Costs Reference
| Operation | Model | Credits |
|---|---|---|
| Chat message | Claude Haiku | 3 credits |
| Chat message | Claude Sonnet | 8 credits |
| Meta-Doc generation | Claude Haiku | 18 credits |
| Meta-Doc generation | Claude Sonnet | 45 credits |
| Ingestion | (per page) | 1 credit |

## Definition of Done
- [ ] `POST /v1/chat/message` streams tokens within 3 seconds of request
- [ ] Multi-turn works: second message receives context of first exchange
- [ ] `GET /v1/chat/sessions` returns correct sessions for user (not other users)
- [ ] Session auto-created and `session_id` in first SSE event
- [ ] Credits deducted after successful response (not before)
- [ ] `402` returned for insufficient credits (before retrieval)
- [ ] Tenant isolation test passes (user A cannot access user B's sessions)
- [ ] Alembic migration creates `chat_sessions` table cleanly
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Run integration tests:
uv run pytest tests/integration/api/test_chat_endpoints.py -v

# Manual streaming test:
TOKEN="your_clerk_token"

# Step 1: Send first message (no session_id — will auto-create)
curl -N -X POST http://localhost:8000/v1/chat/message \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"message": "What ML projects have I worked on?", "profile_id": "your-profile-uuid", "model": "haiku"}'
# Expected stream:
# data: {"type": "session", "session_id": "uuid-here"}
# data: {"type": "token", "content": "Based on your memories"}
# data: {"type": "token", "content": ", you have worked on..."}
# data: {"type": "done", "citations": [...], "credits_consumed": 3}

# Step 2: Multi-turn (use session_id from step 1)
curl -N -X POST http://localhost:8000/v1/chat/message \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"message": "Which of those used PyTorch?", "session_id": "uuid-from-step-1", "profile_id": "your-profile-uuid", "model": "haiku"}'
# Expected: response references previous context about ML projects

# List sessions:
curl http://localhost:8000/v1/chat/sessions \
  -H "Authorization: Bearer ${TOKEN}"

# Quality gate:
make quality
```

**Passing result:** Tokens stream within 3 seconds. Session created and returned. Second message uses conversation history. Credits deducted. Tenant isolation test passes.

---

## Agent Implementation Brief

```
Implement STORY-026: Conversational Memory Chat — Backend.

Read first:
1. CLAUDE.md (architecture rules — RULE 2 tenant isolation, RULE 6 lazy imports)
2. docs/architecture/03-api-contract.md (understand existing endpoint conventions)
3. docs/architecture/02-database-schema.md (follow table naming conventions for chat_sessions)
4. docs/architecture/04-background-jobs.md (SSE pattern — chat does NOT use ARQ)
5. docs/stories/EPIC-05-metadoc/STORY-015.md (RAGService.retrieve() to reuse)
6. docs/stories/EPIC-09-memory-intelligence/STORY-026.md (this file)

Key constraints:
- Write ChatSession model + ChatMessageRequest schema FIRST (RULE 4)
- Write tests SECOND, implementation THIRD
- Chat uses direct SSE streaming — NOT ARQ queue (interactive UX requires instant response)
- asyncio.timeout(60) inside the event generator
- from anthropic import ... inside function body (# noqa: PLC0415)
- Qdrant search MUST include tenant_id filter (FieldCondition key="tenant_id")
- 402 credit check BEFORE any retrieval or LLM call
- session_id returned in FIRST SSE event (type="session")
- Only last 6 messages passed to LLM as history

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# 1. Quality gate:
make quality && make test

# 2. Commit:
git add -A && git commit -m "feat(ravenbase): STORY-026 conversational memory chat backend"
git push

# 3. Regenerate client (this story adds new endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-026"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-026
git add docs/stories/epics.md && git commit -m "docs: mark STORY-026 complete"
```
