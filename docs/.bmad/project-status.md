# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 7
**Status:** In progress — 7 of 37 stories complete

**Next story to implement:** STORY-010
**Story file:** `docs/stories/EPIC-02-ingestion/STORY-010.md`

---

## Last Completed Story

**STORY-009 — Entity Extraction + Neo4j Writer** (2026-03-26)
LLMRouter (Gemini 2.5 Flash primary, Claude Haiku fallback, 429 backoff). GraphService per-chunk extraction with `ExtractionResult` Pydantic schema. MERGE Concept nodes (dedup by `{name, tenant_id}`), CREATE Memory nodes, EXTRACTED_FROM + RELATES_TO relationships. `graph_extraction` ARQ task registered in WorkerSettings, triggered automatically by `parse_document` and `ingest_text`. `QdrantAdapter.scroll_by_source` for paginated chunk retrieval. 90 tests passing, `make quality` clean.

---

## Context for Next Session

STORY-009 merged to main. `graph_extraction` is now live and triggered automatically after `parse_document` and `ingest_text` complete. story-counter is now 010. Next up is STORY-010 — Graph API endpoints (REST endpoints for node + neighborhood queries, still in ravenbase-api). The full STORY-008 row in epics.md will only flip to ✅ after the frontend Omnibar UI (AC-6..AC-8) in ravenbase-web completes in Phase B.

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
