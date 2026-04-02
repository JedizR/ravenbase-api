# GenerationEngine

> **Component ID:** BE-COMP-04
> **Epic:** EPIC-05 — Meta-Document Generation, EPIC-09 — Memory Intelligence
> **Stories:** STORY-016, STORY-017, STORY-026, STORY-027
> **Type:** Cross-repo (Backend + Frontend)

---

## Purpose

The GenerationEngine owns all LLM-driven synthesis in Ravenbase: streaming Meta-Document generation (via ARQ + Redis pub/sub SSE) and Conversational Memory Chat (direct SSE, no queue). It retrieves context from `RAGService`, masks PII via Presidio, streams tokens to the browser, persists results to PostgreSQL and Neo4j, and deducts credits from the user's balance on success.

---

## User Journey

**Meta-Document generation:**
1. User navigates to `/workstation`, types a prompt
2. Clicks "Generate" → `POST /v1/metadoc/generate {prompt, profile_id, model?}`
3. Backend checks credits (402 if insufficient)
4. Returns `{job_id, estimated_credits}` immediately
5. Frontend opens SSE: `GET /v1/metadoc/stream/{job_id}?token={clerk_jwt}`
6. ARQ worker: retrieves context → masks PII → streams tokens via Redis pub/sub
7. Browser renders Markdown tokens in real-time
8. `{type: "done", doc_id, credits_consumed}` event → document saved, credits deducted
9. Editor shows `◆ SAVED_JUST_NOW`; history panel refreshes

**Memory Chat:**
1. User navigates to `/chat`, types a message
2. `POST /v1/chat/message {message, session_id?, profile_id, model}` — direct SSE (no ARQ)
3. Backend checks credits → retrieves context → streams tokens directly
4. First token within 3 seconds
5. `{type: "done", citations: [...], credits_consumed}` — citation cards appear
6. Clicking citation navigates to `/graph?node={memory_id}`

---

## Admin Bypass

Credit costs per operation:
- Meta-Doc: 18 credits (Haiku), 45 credits (Sonnet)
- Chat: 3 credits (Haiku), 8 credits (Sonnet)

Admin users: `CreditService.check_or_raise()` returns early → LLM runs → `CreditService.deduct()` returns zero-amount transaction → balance unchanged.

Frontend behavior for admin users: same UI, sidebar shows `◆ ADMIN_ACCESS` instead of credit count.

See `BE-COMP-06-CreditSystem.md` for the full admin bypass implementation.

---

## Known Bugs / Current State

**⚠️ ROUTE CORRECTIONS (docs errors in this file):**
The following routes are referenced incorrectly throughout this file's subcomponents:
- `WRONG: /workstation` → `CORRECT: /workstation`
- `WRONG: /chat` → `CORRECT: /chat`
- `WRONG: /graph` → `CORRECT: /graph`
Next.js route groups do NOT add URL segments. See CLAUDE.md Architecture section.

**BUG-016 (HIGH — RULE-19 violation):** Workstation auto-save not implemented.
- MetaDocEditor shows `◆ SAVED_JUST_NOW` / `◆ UNSAVED_CHANGES` labels but never calls `localStorage.setItem()`. The `use-autosave.ts` hook exists but is not connected to editor content.
- **Fix:** Wire `useAutosave(content, "ravenbase-draft-${profileId}", 30_000)` in `MetaDocEditor.tsx`.
- **Story:** STORY-039. See `FE-COMP-07-Workstation.md` for full fix.

**BUG-017 (HIGH):** MetaDocHistory clicking a previous doc loads empty content.
- Clicking history item sets `activeContent=""` — fetch result never updates state correctly.
- **Fix:** See `FE-COMP-07-Workstation.md` for the `useEffect` fix.
- **Story:** STORY-039

**BUG-022 (MEDIUM — memory leak):** MemoryChat `ReadableStream.getReader()` not cancelled on unmount.
- **Root cause:** `components/domain/MemoryChat.tsx:161` — the stream reader is not closed in a cleanup function when the component unmounts. If user navigates away during streaming, the reader continues consuming.
- **Fix:** Store reader in `useRef`, call `reader.cancel()` in the `useEffect` cleanup.
- **Story:** STORY-039

---

## Acceptance Criteria

- [ ] `POST /v1/metadoc/generate` returns `{job_id, estimated_credits}` immediately
- [ ] SSE stream delivers tokens in real-time via `GET /v1/metadoc/stream/{job_id}?token=`
- [ ] `402` returned before ANY LLM call when credits insufficient
- [ ] Credits deducted AFTER successful generation, not before
- [ ] PII masked in LLM input when `ENABLE_PII_MASKING=true`
- [ ] `MetaDocument` saved to PostgreSQL after generation
- [ ] `CONTAINS` edges written to Neo4j for each contributing memory
- [ ] Admin users: generation runs, 0 credits deducted
- [ ] Chat first token within 3 seconds of POST
- [ ] Chat session auto-created when no `session_id` provided
- [ ] Multi-turn: last 6 messages passed to LLM as conversation history
- [ ] Citation data in `done` event: `{memory_id, content_preview, source_filename}`
- [ ] Auto-save to localStorage every 30 seconds in Workstation (BUG-016 fixed)
- [ ] Click history item → `content_markdown` loaded correctly (BUG-017 fixed)
- [ ] Stream reader cancelled on component unmount (BUG-022 fixed)

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `docs/design/04-ux-patterns.md` — streaming SSE patterns, auto-save state machine
- `BE-COMP-03-RetrievalEngine.md` — `RAGService.retrieve()` used by both generation flows
- `BE-COMP-06-CreditSystem.md` — credit costs, admin bypass
- `BE-COMP-07-PrivacyLayer.md` — PII masking (Presidio) integration
- `FE-COMP-07-Workstation.md` — workstation UI, BUG-016, BUG-017 fixes
- `docs/architecture/03-api-contract.md` — `/v1/metadoc/generate`, `/v1/chat/message` endpoints
- `docs/components/REFACTOR_PLAN.md` — BUG-016, BUG-017, BUG-022 fix details

---

## Goal

The GenerationEngine owns all LLM-driven synthesis in Ravenbase: Meta-Document generation with SSE streaming, and Conversational Memory Chat. It retrieves context via COMP-03, masks PII via COMP-07, streams tokens to the browser, and persists generated content to PostgreSQL and Neo4j. Every generation operation deducts credits from the user's balance.

---

## Product Requirements

1. **Meta-Doc Generation Endpoint:** `POST /v1/metadoc/generate` accepts `{prompt, profile_id, model}` and returns `{job_id, estimated_credits}`. Credits are checked BEFORE enqueuing the ARQ job. Returns `402` if insufficient.

2. **Meta-Doc SSE Streaming:** `GET /v1/metadoc/stream/{job_id}` returns `text/event-stream`. Tokens stream via Redis pub/sub: `metadoc:stream:{job_id}`. Final event is `{type: "done", doc_id, credits_consumed}`.

3. **Model Selection:** Model resolution order: request body `model` → user's `preferred_model` → Haiku default. `"haiku"` maps to `"claude-haiku-4-5-20251001"`, `"sonnet"` maps to `"claude-sonnet-4-6"`.

4. **Credit Costs:** Meta-Doc synthesis: 18 credits (Haiku) or 45 credits (Sonnet). Credits deducted AFTER successful generation, never before.

5. **PII Masking:** Presidio runs on all retrieved chunks before sending to LLM (when `ENABLE_PII_MASKING=true`). Deterministic entity map ensures same placeholder across all chunks in one generation.

6. **LLM Output Sanitization:** `bleach.clean()` sanitizes all LLM output before writing to PostgreSQL. Never use `dangerouslySetInnerHTML` for LLM-generated content in frontend.

7. **Generation Timeout:** 5-minute timeout via `asyncio.wait_for`. On timeout: SSE emits `{type: "error", message: "Generation timed out"}`, no partial document saved, no credits deducted.

8. **MetaDocument Persistence:** After generation, `MetaDocument` record saved to PostgreSQL with `CONTAINS` edges to contributing Memory nodes in Neo4j.

9. **Provider Outage Handling:** If Anthropic returns 5xx during streaming: catch, emit error SSE event, do NOT charge credits.

10. **Chat Endpoint:** `POST /v1/chat/message` accepts `{message, session_id?, profile_id, model}` and streams `text/event-stream` with direct SSE (NOT ARQ). First token arrives within 3 seconds.

11. **Chat Session Management:** `GET /v1/chat/sessions` returns paginated session list (newest first). `GET /v1/chat/sessions/{id}` returns full session. `DELETE /v1/chat/sessions/{id}` deletes session. Session auto-created on first message if no `session_id`.

12. **Multi-turn Chat Context:** Last 6 messages from session passed to LLM as conversation history. `session_id` returned in first SSE event so client can track multi-turn.

13. **Chat Credit Costs:** 3 credits (Haiku) or 8 credits (Sonnet) per message, checked BEFORE retrieval starts. `402` returned if insufficient.

14. **Chat Citations:** Final SSE `{type: "done"}` event includes `citations: [{memory_id, content_preview, source_filename}]`. Clicking a citation opens Graph Explorer with that node.

15. **Workstation UI:** `/workstation` renders streaming Meta-Doc output with Markdown rendering, export to MD, and "Last saved" status indicator using ◆ mono label pattern.

16. **Chat UI:** `/chat` renders with sidebar (session list) + main chat area. Token streaming with cursor. Citation cards after each AI message. Mobile: session drawer, fixed input.

17. **Model Selector:** Both Meta-Doc and Chat UIs show Haiku/Sonnet selector with credit cost displayed next to each option.

---

## Criteria and Tests

| Criterion | Test |
|---|---|
| Meta-Doc streams tokens to browser | `curl -N` to stream endpoint → tokens arrive incrementally |
| 402 returned before job enqueued | Set credits to 0 → call generate → 402 immediately |
| Credits deducted after success | Complete generation → check CreditTransaction record |
| 5-minute timeout clean | Mock slow LLM → generate → error event after 5min, no partial doc |
| Provider outage → no charge | Anthropic returns 500 → SSE error event, credits unchanged |
| PII masked in LLM input | Send "John Smith" in context → verify placeholder in LLM payload |
| MetaDocument saved to PostgreSQL | Complete generation → check metadocs table |
| CONTAINS edges in Neo4j | Complete generation → check Neo4j for CONTAINS edges |
| Chat first token < 3s | Time from POST to first token → < 3s |
| Multi-turn context preserved | Send 2 messages in same session → second uses first as context |
| Chat credits deducted | Send message → check CreditTransaction for deduction |
| 402 for chat insufficient credits | Credits to 0 → send chat message → 402 before retrieval |
| Session auto-created | POST without session_id → session created, id in first event |
| Citation opens Graph Explorer | Click citation → router.push to /graph?node={memory_id} |
| Workstation renders Markdown | Meta-Doc streams → Markdown renders in real-time |
| Mobile chat: fixed input | Resize to 375px → input sticky at bottom |

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-016](../stories/EPIC-05-metadoc/STORY-016.md) | Meta-Doc Generation Worker + Streaming | Backend | ARQ task, SSE, PII masking, MetaDocument save |
| [STORY-017](../stories/EPIC-05-metadoc/STORY-017.md) | Workstation UI | Frontend | Streaming editor, Markdown render, export |
| [STORY-026](../stories/EPIC-09-memory-intelligence/STORY-026.md) | Conversational Memory Chat — Backend | Backend | Direct SSE chat, session management, citations |
| [STORY-027](../stories/EPIC-09-memory-intelligence/STORY-027.md) | Conversational Memory Chat — Frontend | Frontend | Chat UI, session sidebar, citation cards, mobile |

---

## Subcomponents

The GenerationEngine decomposes into 4 subcomponents.

---

### SUBCOMP-04A: Meta-Doc Generation Worker + SSE

**Stories:** STORY-016
**Files:** `src/workers/metadoc_tasks.py`, `src/api/routes/metadoc.py`, `src/schemas/metadoc.py`, `src/adapters/anthropic_adapter.py`, `src/adapters/presidio_adapter.py`, `tests/integration/api/test_metadoc_endpoints.py`

#### Details
The `generate_meta_document` ARQ task retrieves context via RAGService, masks PII via Presidio, streams tokens to Redis pub/sub, and saves the completed MetaDocument. The SSE endpoint subscribes to Redis and re-streams to the browser. Credit check (402) happens BEFORE job enqueue. Credits deducted AFTER successful generation.

#### Criteria of Done
- [ ] `POST /v1/metadoc/generate` returns `{job_id, estimated_credits}` and enqueues ARQ job
- [ ] `GET /v1/metadoc/stream/{job_id}` returns SSE stream
- [ ] Tokens stream via Redis `metadoc:stream:{job_id}` channel
- [ ] `402` returned when credits insufficient BEFORE job enqueued
- [ ] Credits deducted AFTER generation completes successfully
- [ ] Presidio PII masking runs on context chunks before LLM call (`ENABLE_PII_MASKING=true`)
- [ ] Deterministic entity map: same PII → same placeholder across all chunks
- [ ] `bleach.clean()` sanitizes LLM output before DB write
- [ ] 5-minute timeout: `asyncio.wait_for` → error event, no partial save
- [ ] Anthropic 5xx: error event emitted, no credits charged
- [ ] `MetaDocument` saved to PostgreSQL on completion
- [ ] `CONTAINS` edges written to Neo4j for each contributing memory

#### Checklist
- [ ] `GenerateRequest`, `GenerateResponse` schemas in `src/schemas/metadoc.py`
- [ ] Credit check: `user.credits_balance < estimated_credits` → raise 402 BEFORE `enqueue_job`
- [ ] `enqueue_meta_document` called after credit check passes
- [ ] `from anthropic import ...` inside function body (`# noqa: PLC0415`)
- [ ] `asyncio.timeout(300)` wraps LLM streaming call
- [ ] Redis publish per token + final `done` event
- [ ] `PresidioAdapter` called before LLM with masked chunks
- [ ] `bleach.clean(content, tags=ALLOWED_TAGS)` on LLM output before DB
- [ ] `MetaDocument` write in `finally` block to handle partial failures
- [ ] Credit deduction after successful write (not before)
- [ ] `MODEL_MAP`: haiku → `claude-haiku-4-5-20251001`, sonnet → `claude-sonnet-4-6`
- [ ] Credit costs: 18 (haiku), 45 (sonnet)

#### Testing
```bash
# Manual SSE streaming test:
TOKEN="your_clerk_token"
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/metadoc/generate \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize my Python skills", "profile_id": "UUID", "model": "sonnet"}')
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
curl -N "http://localhost:8000/v1/metadoc/stream/${JOB_ID}?token=${TOKEN}"
# Expected: data: {"type":"token","content":"Here is..."}  (streaming)
#           data: {"type":"done","doc_id":"...","credits_consumed":45}

# Test 402:
# Set user credits to 0
curl -X POST http://localhost:8000/v1/metadoc/generate \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize", "model": "sonnet"}'
# Expected: 402 {"detail": "Insufficient credits"}

make quality
```

---

### SUBCOMP-04B: Workstation UI

**Stories:** STORY-017
**Files:** `components/domain/MetaDocEditor.tsx`, `components/domain/ExportButton.tsx`, `app/(dashboard)/workstation/page.tsx`, `app/(dashboard)/workstation/loading.tsx`, `hooks/use-sse.ts`

#### Details
The Workstation is where users generate and refine Meta-Documents. It renders streaming Markdown output as tokens arrive, shows a "Last saved" status indicator in the header, and provides MD export. The SSE streaming pattern reuses the `use-sse.ts` hook from STORY-007. On mobile, the layout stacks vertically with a fixed bottom input area.

#### Criteria of Done
- [ ] Workstation accessible at `/workstation`
- [ ] SSE stream renders Markdown tokens in real-time (streaming cursor ▌ visible)
- [ ] Markdown rendered with `react-markdown` + `remark-gfm`
- [ ] "Last saved" status indicator in header: "◆ SAVED_JUST_NOW" → "◆ SAVED_2_MIN_AGO" → "◆ UNSAVED_CHANGES"
- [ ] Save to localStorage every 30 seconds while editing
- [ ] Export button: downloads content as `.md` file
- [ ] Model selector (Haiku/Sonnet) with credit cost shown
- [ ] Mobile: stacked layout with fixed bottom input
- [ ] Loading skeleton on navigation
- [ ] aria-live region for streaming output (accessibility)
- [ ] Dynamic import of `react-markdown` (not in initial bundle)

#### Checklist
- [ ] `use-sse.ts` hook reused for SSE connection (from STORY-007)
- [ ] `react-markdown` + `remark-gfm` for Markdown rendering
- [ ] Dynamic import of `react-markdown` components
- [ ] "◆ SAVED_JUST_NOW" / "◆ SAVED_2_MIN_AGO" / "◆ UNSAVED_CHANGES" in header
- [ ] `localStorage.setItem` every 30 seconds during editing
- [ ] `Blob` download for MD export: `URL.createObjectURL(new Blob([content], {type: "text/markdown"})`
- [ ] Credit cost displayed next to model selector
- [ ] `aria-live="polite"` on streaming output region
- [ ] `useRef` for SSE connection (not state — avoids re-renders)
- [ ] Loading skeleton: `app/(dashboard)/workstation/loading.tsx`
- [ ] Mobile: `flex-col` stacked layout, `sticky bottom-0` input

#### Testing
```bash
# Manual test:
# 1. Navigate to http://localhost:3000/workstation
# 2. Type prompt "Generate my resume"
# 3. Verify: tokens stream in real-time with cursor
# 4. Verify: Markdown renders as tokens arrive
# 5. Wait for completion → verify "◆ SAVED_JUST_NOW" in header
# 6. Click Export → verify .md file downloads
# 7. Resize to 375px → verify stacked mobile layout

npm run build
# Expected: 0 TypeScript errors
```

---

### SUBCOMP-04C: Conversational Memory Chat — Backend

**Stories:** STORY-026
**Files:** `src/models/chat_session.py`, `src/api/routes/chat.py`, `src/services/chat_service.py`, `src/schemas/chat.py`, `alembic/versions/XXX_add_chat_sessions.py`, `tests/integration/api/test_chat_endpoints.py`

#### Details
The chat backend provides conversational memory exploration via direct SSE streaming (NOT ARQ — chat must feel instant with < 3s to first token). It reuses `RAGService.retrieve()` for context, streams Claude tokens, manages multi-turn session state in PostgreSQL, and deducts credits. Sessions auto-create on first message.

#### Criteria of Done
- [ ] `POST /v1/chat/message` accepts `{message, session_id?, profile_id, model}` and streams SSE
- [ ] First token arrives at client within 3 seconds
- [ ] Session auto-created on first message if no `session_id`; `session_id` in first SSE event
- [ ] Multi-turn: last 6 messages passed to LLM as conversation history
- [ ] `GET /v1/chat/sessions` returns paginated session list, newest first
- [ ] `GET /v1/chat/sessions/{id}` returns full session with all messages
- [ ] `DELETE /v1/chat/sessions/{id}` deletes session (tenant-scoped)
- [ ] 3 credits (Haiku) or 8 credits (Sonnet) per message, deducted after response
- [ ] `402` returned BEFORE retrieval if insufficient credits
- [ ] Citation extraction: `citations: [{memory_id, content_preview, source_filename}]` in `done` event
- [ ] Tenant isolation: sessions scoped to `user_id`, Qdrant retrieval scoped to `tenant_id`
- [ ] 60-second timeout on LLM streaming

#### Checklist
- [ ] `ChatSession` SQLModel with `messages: list[dict]` JSON column
- [ ] Alembic migration for `chat_sessions` table
- [ ] `ChatMessageRequest`, `ChatSessionResponse`, `CitationItem` schemas in `src/schemas/chat.py`
- [ ] Direct SSE streaming from route handler — NOT via ARQ queue
- [ ] `session_id` yielded in FIRST SSE event: `{"type": "session", "session_id": "..."}`
- [ ] Last 6 messages: `session.messages[-6:]` passed to LLM
- [ ] `from anthropic import ...` inside function body (`# noqa: PLC0415`)
- [ ] `asyncio.timeout(60)` on LLM streaming
- [ ] Credit check: `await credit_service.check_or_raise(...)` BEFORE retrieval
- [ ] Credits deducted: `await credit_service.deduct(...)` AFTER successful response
- [ ] `build_system_prompt()`: formats retrieved chunks with source attribution
- [ ] `extract_citations()`: extracts `{memory_id, content_preview, source_filename}` from chunks
- [ ] `get_or_create_session()`: creates session if `session_id` is None
- [ ] Always check session belongs to current user before delete
- [ ] `MODEL_MAP`: haiku → `claude-haiku-4-5-20251001`, sonnet → `claude-sonnet-4-6`

#### Testing
```bash
# Streaming test:
TOKEN="your_clerk_token"
curl -N -X POST http://localhost:8000/v1/chat/message \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"message": "What ML projects have I worked on?", "profile_id": "UUID", "model": "haiku"}'
# Expected:
# data: {"type": "session", "session_id": "uuid-here"}
# data: {"type": "token", "content": "Based on your memories"}
# data: {"type": "done", "citations": [...], "credits_consumed": 3}

# Multi-turn:
# Use session_id from first call, send follow-up
# Expected: second response references context from first

# Session list:
curl http://localhost:8000/v1/chat/sessions -H "Authorization: Bearer ${TOKEN}"

make quality
```

---

### SUBCOMP-04D: Conversational Memory Chat — Frontend

**Stories:** STORY-027
**Files:** `app/(dashboard)/chat/page.tsx`, `components/domain/MemoryChat.tsx`, `components/domain/ChatSessionSidebar.tsx`, `components/domain/ChatMessage.tsx`, `components/domain/CitationCard.tsx`

#### Details
The Memory Chat UI provides a conversational interface at `/chat` with a session sidebar, real-time token streaming, and clickable citation cards that navigate to the Graph Explorer. It uses the `useApiFetch()` hook for non-streaming calls and native `fetch` with streaming reader for the chat SSE endpoint.

#### Criteria of Done
- [ ] Chat page at `/chat` renders with sidebar (session list) + main chat area
- [ ] User types message, presses Enter → tokens stream in real-time with cursor ▌
- [ ] First SSE event `session` captures `session_id` for multi-turn tracking
- [ ] AI message bubble fills token-by-token as streaming response arrives
- [ ] Final `done` event renders citation footnotes below the message
- [ ] Clicking citation card navigates to `/graph?node={memory_id}`
- [ ] Sidebar shows all past sessions; clicking loads and resumes that conversation
- [ ] Session title = first 60 chars of first user message
- [ ] Model selector (Haiku/Sonnet) with credit cost shown
- [ ] `402` response shows upgrade prompt modal (not console error)
- [ ] Empty state: "Ask me anything about your memories..."
- [ ] Mobile: session sidebar hidden, accessible via history icon button opening Sheet drawer
- [ ] Mobile: message input fixed to bottom with safe-area padding
- [ ] `h-[100dvh]` used (not `h-screen`) for full-height mobile layouts

#### Checklist
- [ ] `MemoryChat.tsx` is `"use client"` — uses `useState`, `useAuth`, streaming fetch
- [ ] `fetch()` with streaming reader for POST SSE (NOT `EventSource` — POST requires fetch)
- [ ] `Enter` key sends message, `Shift+Enter` inserts newline in textarea
- [ ] No `<form>` tags — textarea with `onKeyDown` handler
- [ ] Citation click: `router.push('/graph?node=${memory_id}')`
- [ ] `useApiFetch()` hook for session list, session load, delete
- [ ] `ChatSessionSidebar`: session list sorted newest-first, click to load
- [ ] Model selector: shadcn `<Select>` component with credit cost display
- [ ] 402 → upgrade modal: catch API error, show modal if status 402
- [ ] Empty state: renders when `messages.length === 0`
- [ ] Mobile `< 768px`: `<Sheet>` drawer for sessions, sticky input at bottom
- [ ] Safe area padding: `pb-[max(1rem,env(safe-area-inset-bottom))]`
- [ ] Optimistic user message: add to list immediately before SSE response
- [ ] `aria-live="polite"` on streaming message region

#### Testing
```bash
# Manual test:
# 1. Navigate to http://localhost:3000/chat
# 2. Verify: empty state message renders
# 3. Type "What Python projects have I worked on?"
# 4. Verify: tokens appear one-by-one (streaming cursor visible)
# 5. Verify: citation cards appear after response completes
# 6. Click a citation → verify Graph Explorer opens with that node
# 7. Send follow-up → verify session_id same (multi-turn context)
# 8. Refresh → verify session in sidebar
# 9. Click session → verify full conversation loads
# 10. Resize to 375px → verify input fixed at bottom, sessions in drawer

npm run build
# Expected: 0 TypeScript errors
```
