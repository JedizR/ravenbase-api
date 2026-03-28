# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 17
**Status:** In progress — 18 of 37 stories complete

**Next story to implement:** STORY-036-BE
**Story file:** `docs/stories/EPIC-10-platform/STORY-036.md`

---

## Last Completed Story

**STORY-029 — Natural Language Graph Query (Backend)** (2026-03-29)
`POST /v1/graph/query` converts natural language to Cypher via LLMRouter("cypher_generation") (Gemini 2.5 Flash primary, Claude Haiku fallback), validates query is read-only, injects tenant_id as a Cypher parameter, executes against Neo4j, and returns nodes/edges/explanation/query_time_ms. Credit cost: 2 per query.

---

## Context for Next Session

STORY-029 merged to main. NL graph query endpoint is live: GraphQueryService uses LLMRouter for Cypher generation, write-keyword safety check, tenant_id parameter injection (RULE 11), and CreditService.deduct(2) before LLM call. Backend sequence continues: [BACKEND GATE]→036-BE→037. STORY-036-BE is the admin dashboard backend (5 endpoints).

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
