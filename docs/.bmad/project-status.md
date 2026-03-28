# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 15
**Status:** In progress — 15 of 37 stories complete

**Next story to implement:** STORY-025
**Story file:** `docs/stories/EPIC-08-polish/STORY-025.md`

---

## Last Completed Story

**STORY-024 — GDPR Account Deletion Cascade** (2026-03-28)
`DELETE /v1/account` endpoint returning 202 and enqueuing `cascade_delete_account` ARQ task. DeletionService orchestrates Storage → Qdrant → Neo4j → PostgreSQL → Clerk deletion with log-and-continue on partial failure. Deterministic `_job_id=f"gdpr:{user_id}"` prevents duplicate jobs. 13 tests added. Tests passing, `make quality` clean.

---

## Context for Next Session

STORY-024 merged to main. GDPR cascade deletion is complete — `DELETE /v1/account` returns 202 and enqueues the cascade job; each step independently try/excepted to ensure partial deletion never aborts the remainder. Backend sequence continues: 025→026→028-BE→029→[BACKEND GATE]→036-BE→037. STORY-025 is PII Masking (Presidio).

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
