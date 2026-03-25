# STORY-008: Text Quick-Capture (Omnibar /ingest)

**Epic:** EPIC-02 — Ingestion Pipeline
**Priority:** P0
**Complexity:** Small
**Depends on:** STORY-006

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (no form tags, apiFetch, Zod validation)
> 3. `docs/architecture/03-api-contract.md` — `POST /v1/ingest/text` endpoint spec
> 4. `docs/design/02-component-library.md` — Omnibar component spec and slash-command pattern
> 5. `docs/design/04-ux-patterns.md` — toast notification patterns (sonner)

---

## User Story
As a user, I want to paste text directly into the Omnibar and have it immediately ingested so that quick captures take less than 5 seconds from paste to searchable.

## Context
- API contract: `architecture/03-api-contract.md` — `POST /v1/ingest/text` request/response shape
- Omnibar component spec: `design/02-component-library.md` — slash-command interface
- UX patterns: `design/04-ux-patterns.md` — toast pattern for confirmation
- Backend: STORY-006 must be complete (text ingest task in `ingestion_tasks.py`)

## Acceptance Criteria
- [ ] AC-1: `POST /v1/ingest/text` accepts `{content, profile_id, tags}` JSON body
- [ ] AC-2: Text up to 50,000 characters accepted; over limit returns `422` with `ErrorCode.TEXT_TOO_LONG`
- [ ] AC-3: Text is chunked (single chunk if < 512 tokens), embedded, and upserted to Qdrant within 10 seconds
- [ ] AC-4: Source record created with `file_type="direct_input"` in PostgreSQL
- [ ] AC-5: Text is searchable via `POST /v1/search` within 15 seconds of ingestion
- [ ] AC-6: Omnibar UI: typing `/ingest` followed by text and pressing Enter triggers ingestion
- [ ] AC-7: Inline confirmation toast: "Captured to [Profile Name]" appears within 2 seconds of Enter
- [ ] AC-8: Omnibar also supports stubs for `/search`, `/profile`, `/generate` (show "command not yet implemented" toast for unimplemented commands)

## Technical Notes

### Files to Create (Backend)
- Add `ingest_text` ARQ task in `src/workers/ingestion_tasks.py` — simpler than file ingestion (no Docling, no storage)
- Add `POST /v1/ingest/text` endpoint in `src/api/routes/ingest.py` (file should already exist from STORY-005)

### Files to Create (Frontend)
- `components/domain/Omnibar.tsx` — command-palette style input with slash-command routing
- Uses shadcn `Command` component as the base (cmdk pattern)

### Backend: ingest_text Task Pattern
```python
# src/workers/ingestion_tasks.py — add this task
async def ingest_text(
    ctx: Ctx,
    *,
    content: str,
    profile_id: str | None,
    tenant_id: str,
    source_id: str,
    tags: list[str],
) -> dict:
    log = logger.bind(tenant_id=tenant_id, source_id=source_id, job="ingest_text")
    log.info("ingest_text.started", char_count=len(content))

    service = IngestionService()
    # Chunk (if needed), embed, upsert to Qdrant — no Docling needed
    chunks = service.chunk_text(content)  # simple token-based chunking
    embeddings = await service.embed_chunks(chunks, tenant_id, source_id, profile_id)
    await service.upsert_to_qdrant(embeddings, tenant_id)

    log.info("ingest_text.completed", chunk_count=len(chunks))
    return {"chunk_count": len(chunks), "source_id": source_id}
```

### Frontend: Omnibar Slash-Command Routing
```typescript
// components/domain/Omnibar.tsx
const COMMANDS = {
  "/ingest": handleIngest,
  "/search": handleSearch,
  "/profile": handleProfile,
  "/generate": handleGenerate,
  "/inbox": () => router.push("/dashboard/inbox"),
  "/graph": () => router.push("/dashboard/graph"),
};

function parseCommand(input: string): { command: string; args: string } {
  const match = input.match(/^(\/\w+)\s*(.*)/s);
  return match ? { command: match[1], args: match[2].trim() } : { command: "", args: input };
}
```

### Architecture Constraints
- Route calls service, NOT directly calls ARQ or the embedding adapter
- `ingest_text` must be added to `WorkerSettings.functions` in `src/workers/main.py`
- Omnibar uses `apiFetch()` — never raw `fetch()`
- Toast uses `sonner`: `toast.success("Captured to " + profileName)`
- No `<form>` tags — Enter keypress handled via `onKeyDown`

## Definition of Done
- [ ] Integration test: `test_text_ingest_end_to_end` passes (text → Qdrant searchable within 15s)
- [ ] `POST /v1/ingest/text` with 50,001 chars returns 422
- [ ] Omnibar renders in dashboard with working `/ingest` command
- [ ] `make quality` passes (0 errors)
- [ ] `npm run build` passes (0 TypeScript errors)

## Testing This Story

```bash
# Backend integration test:
uv run pytest tests/integration/workers/test_ingestion_tasks.py::test_ingest_text -v

# Manual API test:
curl -X POST http://localhost:8000/v1/ingest/text \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "I use TypeScript for all projects.", "profile_id": null, "tags": []}'
# Expected: 202 {"job_id": "...", "source_id": "...", "status": "queued"}

# Test character limit:
curl -X POST http://localhost:8000/v1/ingest/text \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d "{\"content\": \"$(python3 -c "print('a'*50001)")\"}"
# Expected: 422 {"detail": {"code": "TEXT_TOO_LONG", ...}}

# Quality:
make quality
npm run build
```

**Passing result:** Text is ingested asynchronously, becomes searchable via `/v1/search` within 15 seconds. Omnibar `/ingest` command triggers the flow from the UI.

---

## Agent Implementation Brief

```
Implement STORY-008: Text Quick-Capture (Omnibar /ingest).

Read first:
1. CLAUDE.md (architecture rules)
2. docs/design/CLAUDE_FRONTEND.md (no form tags, apiFetch, Tailwind only)
3. docs/architecture/03-api-contract.md (POST /v1/ingest/text endpoint spec)
4. docs/design/02-component-library.md (Omnibar component spec)
5. docs/stories/EPIC-02-ingestion/STORY-008.md (this file)

Key constraints:
- ingest_text task must be added to WorkerSettings.functions
- Route calls service → service calls task enqueue (3-layer)
- No <form> tags in Omnibar — use onKeyDown handler
- apiFetch() only — no raw fetch()
- Max 50,000 chars; return 422 with ErrorCode.TEXT_TOO_LONG if exceeded

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
git add -A && git commit -m "feat(ravenbase): STORY-008 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-008"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-008
git add docs/stories/epics.md && git commit -m "docs: mark STORY-008 complete"
```
