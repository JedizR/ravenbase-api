# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 7
**Status:** In progress — 7 of 37 stories complete

**Next story to implement:** STORY-008-BE
**Story file:** `docs/stories/EPIC-02-ingestion/STORY-008.md`

---

## Last Completed Story

**STORY-007 Part 1 — SSE progress stream (Backend)** (2026-03-26)
`GET /v1/ingest/stream/{source_id}?token=` SSE endpoint live. `verify_token_query_param` dependency added for EventSource auth. Redis pub/sub subscriber with try/finally disconnect safety. `ProgressEvent` schema added. 68 tests passing, `make quality` clean. AC-1..AC-5 done; AC-6..AC-7 (frontend) pending.

---

## Context for Next Session

STORY-007 backend merged to main. SSE endpoint at `GET /v1/ingest/stream/{source_id}?token=<clerk_jwt>` streams Redis pub/sub events (`job:progress:{source_id}`) as `text/event-stream`. Stream closes on `status=completed` or `status=failed`. `verify_token_query_param` reads JWT from query param (EventSource cannot set headers). Before starting STORY-007 Part 2 (frontend), run `npm run generate-client` in `ravenbase-web` to pick up the new endpoint. Frontend needs `IngestionProgress` component + `use-sse.ts` hook.

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
