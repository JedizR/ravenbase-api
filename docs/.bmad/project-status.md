# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 9
**Status:** In progress — 9 of 37 stories complete

**Next story to implement:** STORY-013
**Story file:** `docs/stories/EPIC-04-conflict/STORY-013.md`

---

## Last Completed Story

**STORY-012 — Conflict Detection Worker** (2026-03-27)
Qdrant similarity scan (0.87 threshold, tenant-scoped) + LLM classification via Gemini 2.5 Flash / Haiku fallback. Conflict records written to PostgreSQL, CONTRADICTS / TEMPORAL_LINK Neo4j edges written. Auto-resolution when challenger authority delta ≥ 3. Redis pub/sub notification on `conflict:new:{tenant_id}` after commit. 111 tests passing, `make quality` clean.

---

## Context for Next Session

STORY-012 merged to main. Conflict detection pipeline is live: `parse_document → graph_extraction → scan_for_conflicts` chain. Conflict records appear in PostgreSQL `conflicts` table and CONTRADICTS edges in Neo4j. Next backend story is STORY-013 (Conflict API — list, resolve, undo endpoints).

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
