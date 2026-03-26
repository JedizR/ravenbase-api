# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 5
**Status:** In progress — 6 of 37 stories complete

**Next story to implement:** STORY-007
**Story file:** `docs/stories/EPIC-02-ingestion/STORY-007.md`

---

## Last Completed Story

**STORY-006 — Docling parse + chunk + embed worker** (2026-03-26)
Full ARQ `parse_document` pipeline live: Supabase Storage download, OpenAI moderation pre-check, Docling parse+chunk in executor, OpenAI `text-embedding-3-small` batched embeddings, Qdrant upsert (deterministic UUIDs), Source status transitions (PENDING→PROCESSING→INDEXING→COMPLETED), graph_extraction enqueue. `DoclingAdapter`, `OpenAIAdapter`, `ModerationAdapter` added. 58 tests passing, `make quality` clean.

---

## Context for Next Session

STORY-006 merged to main. `parse_document` ARQ task fully replaces the stub — downloads from Supabase Storage, runs moderation, Docling parse+chunk in executor, embeds with OpenAI, upserts to Qdrant, then enqueues `graph_extraction`. Docling uses `DocumentStream` + `converter.convert()` API (not `convert_from_bytes`). STORY-007 implements the SSE progress stream via Redis pub/sub so the frontend can observe ingestion in real time.

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
