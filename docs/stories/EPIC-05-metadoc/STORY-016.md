# STORY-016: Meta-Doc Generation Worker + Streaming

**Epic:** EPIC-05 — Meta-Document Generation
**Priority:** P0
**Complexity:** Large
**Depends on:** STORY-015

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 3: ARQ, RULE 6: lazy imports)
> 2. `docs/architecture/04-background-jobs.md` — ARQ task pattern + SSE re-streaming
> 3. `docs/architecture/03-api-contract.md` — `POST /v1/metadoc/generate` + `GET /v1/metadoc/stream/{job_id}` specs
> 4. `docs/architecture/05-security-privacy.md` — Presidio PII masking integration point
> 5. `docs/architecture/02-database-schema.md` — MetaDocument model, CreditTransaction model

---

## User Story
As a user, I want to type a prompt and watch my Meta-Document stream into existence in real-time.

## Acceptance Criteria
- [ ] AC-1: `POST /v1/metadoc/generate` accepts `{prompt, profile_id, model}`, returns `{job_id, estimated_credits}`
- [ ] AC-2: `GET /v1/metadoc/stream/{job_id}` SSE stream emits `{type: "token", content: "..."}` events
- [ ] AC-3: PII masking via Presidio runs on all retrieved chunks before sending to LLM (when `ENABLE_PII_MASKING=true`)
- [ ] AC-4: System prompt enforces output format: Markdown, professional tone, cite sources
- [ ] AC-5: Claude Sonnet streams tokens back; SSE endpoint re-streams to client
- [ ] AC-6: Final event: `{type: "done", doc_id: uuid, credits_consumed: int}`
- [ ] AC-7: MetaDocument saved to PostgreSQL; contributing memory IDs saved
- [ ] AC-8: CONTAINS edges written to Neo4j for each contributing memory
- [ ] AC-9: If user has insufficient credits: `402 Payment Required` before starting job
- [ ] AC-10: Generation timeout: 5 minutes; if exceeded, stream `{type: "error", message: "Generation timed out"}`

## Technical Notes

### Files to Create (Backend)
- `src/workers/metadoc_tasks.py` — `generate_meta_document` ARQ task with streaming
- `src/adapters/anthropic_adapter.py` — add `stream_completion()` for SSE-compatible streaming
- `src/adapters/presidio_adapter.py` — PII masking with deterministic entity map
- `src/api/routes/metadoc.py` — `/v1/metadoc/generate` + `/v1/metadoc/stream/{job_id}` SSE endpoints
- `src/schemas/metadoc.py` — GenerateRequest, GenerateResponse Pydantic schemas
- `tests/integration/api/test_metadoc_endpoints.py`

### Architecture Constraints
- PII masking MUST run before any content is sent to Anthropic (when `ENABLE_PII_MASKING=true`)
- Credits MUST be deducted AFTER successful generation (not before)
- 402 check MUST happen BEFORE enqueueing ARQ job
- `anthropic` import inside function body (`# noqa: PLC0415`)
- LLM output MUST be sanitized with `bleach.clean()` before writing to the database.
  See `docs/architecture/05-security-privacy.md` → Layer 12 for the full sanitization
  pattern and `ALLOWED_TAGS` list. Import: `import bleach` (this import is safe at
  module level — bleach is a utility library, not a heavy ML dependency)
- Generation timeout: `asyncio.wait_for(..., timeout=300)`
- Model resolution order: request body `model` → user's `preferred_model` → Haiku default
- Streaming generation uses `anthropic_adapter.py` directly (has custom SSE logic) — NOT `llm_router.py`
- If Anthropic returns 5xx during streaming: catch, emit `{type: "error", message: "Generation temporarily unavailable. Please try again."}` SSE event, do NOT charge credits
- Provider outage during streaming: user sees error toast, credits never deducted
- Map aliases: `"haiku"` → `"claude-haiku-4-5-20251001"`, `"sonnet"` → `"claude-sonnet-4-6"`
- Credit cost: Haiku synthesis = 18 credits, Sonnet synthesis = 45 credits
- Pattern:
  ```python
  MODEL_MAP = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-4-6"}
  raw = model_override or user.get("preferred_model", "claude-haiku-4-5-20251001")
  model = MODEL_MAP.get(raw, raw)
  credit_cost = 45 if "sonnet" in model else 18
  ```

### Credit Costs Reference
| Operation | Model | Credits |
|---|---|---|
| Meta-Doc generation | Claude Haiku | 18 credits |
| Meta-Doc generation | Claude Sonnet | 45 credits |
| Ingestion | (per page) | 1 credit |

### Streaming Pattern
```python
# ARQ task streams tokens to Redis pub/sub: metadoc:stream:{job_id}
# SSE endpoint subscribes and re-streams to client

async def generate_meta_document(ctx, *, prompt, profile_id, tenant_id, job_id):
    from anthropic import AsyncAnthropic  # noqa: PLC0415
    import json

    log = logger.bind(tenant_id=tenant_id, job_id=job_id)
    redis = ctx["redis"]
    client = AsyncAnthropic()

    try:
        async with asyncio.timeout(300):  # 5-minute timeout
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": masked_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    await redis.publish(
                        f"metadoc:stream:{job_id}",
                        json.dumps({"type": "token", "content": text}),
                    )
    except asyncio.TimeoutError:
        await redis.publish(
            f"metadoc:stream:{job_id}",
            json.dumps({"type": "error", "message": "Generation timed out"}),
        )
        return

    # Save MetaDocument to PostgreSQL + write Neo4j CONTAINS edges
    doc_id = await save_meta_document(...)
    await redis.publish(
        f"metadoc:stream:{job_id}",
        json.dumps({"type": "done", "doc_id": str(doc_id), "credits_consumed": credit_cost}),
    )
    log.info("metadoc.generation.completed", doc_id=str(doc_id))
```

### 402 Credit Check (BEFORE enqueue)
```python
@router.post("/generate", response_model=GenerateResponse)
async def generate_meta_document(
    request: GenerateRequest,
    user: dict = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> GenerateResponse:
    estimated_credits = 45 if "sonnet" in request.model else 18
    user_record = await db.get(User, user["user_id"])
    if user_record.credits_balance < estimated_credits:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    job_id = await enqueue_meta_document(
        prompt=request.prompt,
        profile_id=request.profile_id,
        tenant_id=user["user_id"],
    )
    return GenerateResponse(job_id=job_id, estimated_credits=estimated_credits)
```

## Definition of Done
- [ ] All acceptance criteria have passing tests
- [ ] SSE streaming tested end-to-end with EventSource in browser
- [ ] PII masking tested: "John Smith" not in LLM payload when ENABLE_PII_MASKING=true
- [ ] 402 returned when credits insufficient (before job enqueued)
- [ ] MetaDocument saved to PostgreSQL after generation
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Integration tests:
uv run pytest tests/integration/api/test_metadoc_endpoints.py -v

# Manual SSE streaming test:
TOKEN="your_clerk_token"
# Step 1: Start generation
RESPONSE=$(curl -s -X POST http://localhost:8000/v1/metadoc/generate \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize my Python skills", "profile_id": "profile-uuid", "model": "sonnet"}')
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')

# Step 2: Stream result
curl -N "http://localhost:8000/v1/metadoc/stream/${JOB_ID}?token=${TOKEN}"
# Expected: data: {"type":"token","content":"Here is..."}  (streaming)
#           data: {"type":"done","doc_id":"...","credits_consumed":18}

# Test 402:
# Set user credits to 0, then call POST /v1/metadoc/generate
# Expected: 402 {"detail": "Insufficient credits"}

# Quality:
make quality
```

**Passing result:** Tokens stream in real-time to browser. MetaDocument saved. CONTAINS edges in Neo4j. 402 for insufficient credits.

---

## Agent Implementation Brief

```
Implement STORY-016: Meta-Doc Generation Worker + Streaming.

Read first:
1. CLAUDE.md (architecture rules — RULE 3: ARQ, RULE 6: lazy imports)
2. docs/architecture/04-background-jobs.md (ARQ task + SSE re-streaming pattern)
3. docs/architecture/03-api-contract.md (POST /v1/metadoc/generate + stream specs)
4. docs/architecture/05-security-privacy.md (Presidio PII masking)
5. docs/stories/EPIC-05-metadoc/STORY-016.md (this file)

Key constraints:
- Write GenerateRequest, GenerateResponse schemas FIRST (RULE 4)
- 402 credit check BEFORE ARQ enqueue
- Credits deducted AFTER generation (not before)
- `from anthropic import ...` inside function body (# noqa: PLC0415)
- PII masking runs on chunks BEFORE sending to Anthropic (gate on settings.ENABLE_PII_MASKING)
- Streaming: publish tokens to Redis `metadoc:stream:{job_id}` channel
- SSE endpoint subscribes to Redis and re-streams to browser
- asyncio.timeout(300) on generation task — publish error event on timeout

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# 1. Quality gate:
make quality && make test       # backend
npm run build && npm run test   # frontend (if applicable)

# 2. Commit:
git add -A && git commit -m "feat(ravenbase): STORY-016 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-016"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-016
git add docs/stories/epics.md && git commit -m "docs: mark STORY-016 complete"
```
