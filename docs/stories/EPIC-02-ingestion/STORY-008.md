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

### Files to Create/Modify (Backend)
- Add `ingest_text` ARQ task in `src/workers/ingestion_tasks.py`
- Add `POST /v1/ingest/text` endpoint in `src/api/routes/ingest.py`
- Register `ingest_text` in `WorkerSettings.functions` in `src/workers/main.py`

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
    chunks = service.chunk_text(content)
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
- [ ] Integration test: `test_ingest_text` passes
- [ ] `POST /v1/ingest/text` with 50,001 chars returns 422
- [ ] Omnibar renders in dashboard with working `/ingest` command
- [ ] `make quality` passes (0 errors) — backend
- [ ] `npm run build` passes (0 TypeScript errors) — frontend

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

---

## Backend Agent Brief
> Use this brief when opening a session in `ravenbase-api/`

```
Implement STORY-008 Backend: Text Quick-Capture — POST /v1/ingest/text endpoint.

This is a backend-only session. Do NOT touch ravenbase-web.

Read first:
1. CLAUDE.md (architecture rules — mandatory)
2. docs/.bmad/project-status.md (confirm current state)
3. docs/.bmad/journal.md (last 2–3 entries)
4. docs/architecture/03-api-contract.md (POST /v1/ingest/text spec)
5. docs/stories/EPIC-02-ingestion/STORY-008.md (this file)

Scope for this session — backend only:
- Add TextIngestRequest schema to src/schemas/ingest.py
- Add ingest_text ARQ task to src/workers/ingestion_tasks.py
  (no Docling — simple text chunking, embed, upsert to Qdrant)
- Add POST /v1/ingest/text endpoint to src/api/routes/ingest.py
  (202 response, enqueue ingest_text, return UploadResponse)
- Register ingest_text in WorkerSettings.functions in src/workers/main.py
- Add ErrorCode.TEXT_TOO_LONG to src/core/errors.py
- Write integration test: POST /v1/ingest/text happy path → 202
- Write integration test: 50,001 chars → 422 TEXT_TOO_LONG
- Run make quality && make test → 0 failures before committing

After all tests pass:
- Run cd ../ravenbase-web && npm run generate-client to regenerate the
  TypeScript API client (API server must be running at localhost:8000)
  git add src/lib/api-client/
  git commit -m "chore: regenerate client after STORY-008"
  git push && cd ../ravenbase-api

Key constraints:
- Route → Service → ARQ enqueue (3-layer, never skip)
- 50,000 char max; raise_422(ErrorCode.TEXT_TOO_LONG, ...) if exceeded
- Source record must have file_type="direct_input"
- ingest_text uses plain text chunking — NO Docling, NO StorageAdapter
- structlog throughout — no print()

AC-1 through AC-5 are backend scope.
AC-6, AC-7, AC-8 are frontend scope — leave them for the frontend session.

Mark docs state after completion:
- epics.md: do NOT mark ✅ yet — story is only half done
- project-status.md: note STORY-008 backend complete, frontend pending
- story-counter.txt: do NOT increment yet — wait until full story is done
- journal.md: append entry under Sprint 5 for STORY-008-BE

Show plan first. Do not implement yet.
```

---

## Frontend Agent Brief
> Use this brief when opening a session in `ravenbase-web/` (Phase B — journal Sprint 6)

```
Implement STORY-008 Frontend: Omnibar /ingest command UI.

This is a frontend-only session in ravenbase-web. The backend
POST /v1/ingest/text endpoint is already live from the backend session.

Read first:
1. CLAUDE.md (frontend architecture rules — mandatory)
2. docs/.bmad/project-status.md (confirm current state)
3. docs/.bmad/journal.md (last 2–3 entries — check STORY-008-BE notes)
4. docs/design/CLAUDE_FRONTEND.md (no form tags, apiFetch, Tailwind only)
5. docs/design/02-component-library.md (Omnibar component spec)
6. docs/design/04-ux-patterns.md (toast notification patterns)
7. docs/architecture/03-api-contract.md (POST /v1/ingest/text spec)
8. docs/stories/EPIC-02-ingestion/STORY-008.md (this file)

Scope for this session — frontend only:
- Create components/domain/Omnibar.tsx
  - Uses shadcn Command component (cmdk pattern)
  - onKeyDown handler for Enter — NO <form> tags (RULE 1)
  - Slash-command routing: /ingest, /search, /profile, /generate,
    /inbox (router.push), /graph (router.push)
  - /ingest: calls apiFetch POST /v1/ingest/text, shows sonner toast
  - All other commands: toast.info("Command not yet implemented")
- Add Omnibar to the dashboard layout (visible on all dashboard pages)
- Write component test: /ingest command triggers apiFetch
- Write component test: unimplemented commands show correct toast
- npm run build → 0 TypeScript errors before committing

Key constraints:
- apiFetch() only — never raw fetch() (RULE 3)
- No <form> tags — use onKeyDown (RULE 1)
- Tailwind classes only — no inline styles (RULE 2)
- sonner toast: toast.success("Captured to " + profileName)
- TypeScript strict — zero 'any' (RULE 8)

AC-6, AC-7, AC-8 are the scope of this session.
AC-1 through AC-5 were completed in the backend session.

After all tests pass and npm run build is clean:
- epics.md: mark STORY-008 ✅
- story-counter.txt: increment by 1
- project-status.md: update sprint and next story
- journal.md: append entry under Sprint 6 for STORY-008-FE

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Backend quick reference:**
```bash
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-008-BE text ingest endpoint"
git push
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-008"
git push && cd ../ravenbase-api
```

**Frontend quick reference:**
```bash
npm run build && npm run test
git add -A && git commit -m "feat(ravenbase): STORY-008-FE Omnibar /ingest command"
git push
```