# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 16
**Status:** In progress — 17 of 37 stories complete

**Next story to implement:** STORY-029
**Story file:** `docs/stories/EPIC-09-memory-intelligence/STORY-029.md`

---

## Last Completed Story

**STORY-028-BE — AI Chat Context Import Helper (Backend)** (2026-03-29)
`GET /v1/ingest/import-prompt` reads user's Concept nodes from Neo4j scoped by tenant_id + optional profile_id and returns a personalized extraction prompt. New users with no Concept nodes receive a generic fallback prompt (no 404). 4 integration tests added.

---

## Context for Next Session

STORY-028-BE merged to main. Import prompt endpoint is live: IngestionService.get_import_prompt() queries Neo4j via Neo4jAdapter, returns ImportPromptResponse(prompt_text, detected_concepts). Backend sequence continues: 029→[BACKEND GATE]→036-BE→037. STORY-029 is the natural language graph query backend.

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
