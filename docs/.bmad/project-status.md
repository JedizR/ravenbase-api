# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 7
**Status:** In progress — 8 of 37 stories complete

**Next story to implement:** STORY-012
**Story file:** `docs/stories/EPIC-04-conflict/STORY-012.md`

---

## Last Completed Story

**STORY-010 — Graph API Endpoints (nodes + neighborhood)** (2026-03-27)
`GET /v1/graph/nodes` and `GET /v1/graph/neighborhood/{node_id}` endpoints. `GraphNode`, `GraphEdge`, `GraphResponse` Pydantic schemas. `GraphService.get_nodes_for_explorer()` and `get_neighborhood()` with N-hop Cypher traversal. Profile filter via `n.profile_id` property. 102 tests passing, `make quality` clean.

---

## Context for Next Session

STORY-010 merged to main. Graph API endpoints live at `GET /v1/graph/nodes` and `GET /v1/graph/neighborhood/{node_id}`. STORY-011 (Graph Explorer UI) is a frontend story in ravenbase-web and will be implemented in Phase B. Next backend story is STORY-012 (Conflict detection worker — staying in ravenbase-api).

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
