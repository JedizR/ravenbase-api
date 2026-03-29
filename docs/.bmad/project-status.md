# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–18)
**Current sprint:** 18
**Status:** In progress — 19 of 37 stories complete

**Next story to implement:** STORY-037
**Story file:** `docs/stories/EPIC-08-polish/STORY-037.md`

---

## Last Completed Story

**STORY-036-BE — Admin API Endpoints** (2026-03-29)
`require_admin` dependency + 5 endpoints under `/v1/admin/`: paginated user list with email search, user detail with last-20 transactions + source count, credit adjustment with `CreditTransaction(operation="admin_adjustment")` audit trail (allows negative balances), user ban/unban toggle, and platform stats reading Redis `llm:daily_spend:{today}` key via arq_pool.

---

## Context for Next Session

STORY-036-BE merged to main. Admin API is live: `src/api/routes/admin.py`, `src/services/admin_service.py`, `src/api/dependencies/admin.py`. Backend sequence: 036-BE→037. STORY-037 is next.

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
