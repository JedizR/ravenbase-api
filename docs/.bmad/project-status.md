# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 4
**Status:** In progress — 5 of 37 stories complete

**Next story to implement:** STORY-006
**Story file:** `docs/stories/EPIC-02-ingestion/STORY-006.md`

---

## Last Completed Story

**STORY-005 — File upload endpoint + Supabase Storage** (2026-03-26)
`POST /v1/ingest/upload` live: MIME validation (python-magic), SHA-256 dedup, Supabase Storage upload, PostgreSQL Source record, ARQ enqueue, Redis rate limiting. ARQ pool initialised in FastAPI lifespan. `process_ingestion` stub registered. `python-multipart` added. 42 tests passing, `make quality` clean.

---

## Context for Next Session

STORY-005 merged to main. ARQ pool initialized in lifespan (`app.state.arq_pool`). `process_ingestion` stub registered in `WorkerSettings`. `python-multipart` added to `pyproject.toml`. 42 tests passing. STORY-006 implements the full Docling parse + chunk + embed pipeline — budget a full session, it is the largest backend story.

---

## Backend Gate Checklist

Complete these before starting Phase B (frontend):

- [ ] All 17 backend stories merged to main
- [ ] `make test` passes from clean checkout (0 failures)
- [ ] `make quality` passes (0 ruff errors, 0 pyright errors)
- [ ] `npm run generate-client` in ravenbase-web produces a non-empty `src/lib/api-client/`
- [ ] `curl localhost:8000/health` → all 4 services healthy

---

## How to Update This File

After every completed story, update the three fields above:
- **Current sprint** → increment by 1
- **Next story to implement** → next 🔲 row in `docs/stories/epics.md`
- **Last Completed Story** → the story you just finished + one sentence of what was built
- **Context for Next Session** → anything useful to know before starting the next story

**Also update `docs/.bmad/journal.md`** — append one entry for the completed story
following the template at the top of that file. This is mandatory and part of the same
commit (see `DEVELOPMENT_LOOP.md` → Step 9).

The agent that completes each story is responsible for updating all three docs files
as part of the final commit step (see `DEVELOPMENT_LOOP.md` → Post-Story Commit Template).

---

## Session Notes (freehand)

_Use this section for anything that doesn't fit the structure above:
blockers encountered, decisions made, deferred issues, environment quirks._
