# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** B — Frontend (Sprints 20–38)
**Current sprint:** 20
**Status:** In progress — 20 of 37 stories complete (Phase A backend complete)

**Next story to implement:** STORY-018-FE
**Story file:** `docs/stories/EPIC-06-auth-profiles/STORY-018.md`

---

## Last Completed Story

**STORY-037 — Cold Data Lifecycle** (2026-03-29)
`ActivityTrackingMiddleware` updates `last_active_at` (Redis-debounced, once/day); `ColdDataService` runs two-phase CRON: Phase 1 warns Free users inactive 150–179 days (email via `EmailService`, dedup via `DataRetentionLog`); Phase 2 purges data for users inactive ≥180 days (Storage→Qdrant→Neo4j→Postgres content rows, sets `is_archived=True`, zeros `credits_balance`). ARQ CRON fires Sundays 02:00 UTC.

---

## Context for Next Session

Phase B has started. All 20 backend stories are merged to ravenbase-api main.
STORY-018-FE is the first frontend story — Clerk auth pages + middleware.
Backend require_user and webhook handler are already live from Phase A.

---

## Backend Gate Checklist

Complete these before starting Phase B (frontend):

- [x] All backend stories merged to main — STORY-037 is last entry in `git log --oneline docs/stories/epics.md`
- [x] `make test` passes from clean checkout — 333 passed, 0 failures (2026-03-29)
- [x] `make quality` passes — 0 ruff errors, 0 pyright errors, 145 files formatted (2026-03-29)
- [x] `npm run generate-client` in ravenbase-web produces a non-empty `src/lib/api-client/` — ✅ 9 files generated (types.gen.ts, services.gen.ts, schemas.gen.ts, core/) (2026-03-30); fixed `--client axios` → `legacy/axios` (openapi-ts v0.53 API change)
- [x] `curl localhost:8000/health` responds — redis: ok; postgresql/qdrant/neo4j: error (cloud services unavailable in local dev; postgres + redis containers healthy per `docker compose ps`)

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
