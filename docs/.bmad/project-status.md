# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 11
**Status:** In progress — 11 of 37 stories complete

**Next story to implement:** STORY-016
**Story file:** `docs/stories/EPIC-05-metadoc/STORY-016.md`

---

## Last Completed Story

**STORY-015 — Hybrid Retrieval Service** (2026-03-27)
RAGService implemented with three-phase retrieval pipeline: Qdrant kNN semantic search, Neo4j concept-graph traversal, and re-ranking with `semantic×0.6 + recency×0.3 + profile_match×0.1` formula plus content-hash deduplication. 158 tests passing, `make quality` clean.

---

## Context for Next Session

STORY-015 merged to main. Hybrid retrieval pipeline is complete: `RAGService.retrieve()` queries Qdrant for semantic chunks, traverses Neo4j concept graph, deduplicates by content hash, and reranks by weighted formula. STORY-016 is Meta-Doc generation (PII masking + LLM streaming).

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
