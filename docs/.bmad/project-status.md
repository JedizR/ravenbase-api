# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 2
**Status:** In progress — 4 of 37 stories complete

**Next story to implement:** STORY-005
**Story file:** `docs/stories/EPIC-02-ingestion/STORY-005.md`

---

## Last Completed Story

**STORY-004 — ARQ worker setup + health endpoint** (2026-03-26)
WorkerSettings completed with all required fields. `src/workers/utils.py` created with `publish_progress()` (Redis pub/sub) and `update_job_status()` (own DB session). `hello_world` stub task added. 36 tests pass, `make quality` clean, 100% coverage on both new worker files.

---

## Context for Next Session

STORY-004 is complete. All quality gates pass (ruff 0 errors, pyright 0 errors). 36 tests pass. ARQ worker is now fully scaffolded — `make worker` starts the worker. STORY-005 adds file upload endpoint + Supabase Storage — start by reading `docs/stories/EPIC-02-ingestion/STORY-005.md`.

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
