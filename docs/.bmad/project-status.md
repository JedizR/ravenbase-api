# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 14
**Status:** In progress — 14 of 37 stories complete

**Next story to implement:** STORY-024
**Story file:** `docs/stories/EPIC-08-polish/STORY-024.md`

---

## Last Completed Story

**STORY-023 — Credits System** (2026-03-28)
CreditService with SELECT FOR UPDATE for atomic deductions and additions, `GET /v1/credits/balance` returning balance + last 20 transactions, Stripe webhook handler for `checkout.session.completed` credit top-ups, 500-credit signup bonus on `user.created`, ingestion per-page deductions, and meta-doc generation deductions. 15 tests added. Tests passing, `make quality` clean.

---

## Context for Next Session

STORY-023 merged to main. Credits system is complete — CreditService handles all atomic credit mutations, Stripe webhook top-ups work, and signup bonus is applied via `user.created`. Backend sequence continues: 024→025→026→028-BE→029→[BACKEND GATE]→036-BE→037. STORY-024 is GDPR account deletion cascade.

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
