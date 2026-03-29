# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–19) — COMPLETE
**Current sprint:** 19
**Status:** COMPLETE — 20 of 37 stories complete (all backend stories done)

**Next story to implement:** N/A — Backend Gate Checklist must pass before Phase B (frontend)
**Story file:** N/A

---

## Last Completed Story

**STORY-037 — Cold Data Lifecycle** (2026-03-29)
`ActivityTrackingMiddleware` updates `last_active_at` (Redis-debounced, once/day); `ColdDataService` runs two-phase CRON: Phase 1 warns Free users inactive 150–179 days (email via `EmailService`, dedup via `DataRetentionLog`); Phase 2 purges data for users inactive ≥180 days (Storage→Qdrant→Neo4j→Postgres content rows, sets `is_archived=True`, zeros `credits_balance`). ARQ CRON fires Sundays 02:00 UTC.

---

## Context for Next Session

STORY-037 merged to main. All backend stories complete. Before starting Phase B (frontend work), complete the Backend Gate Checklist below.

---

## Backend Gate Checklist

Complete these before starting Phase B (frontend):

- [x] All backend stories merged to main (STORY-037 was the final backend story)
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
