# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 6
**Status:** In progress — 6 of 37 stories complete

**Next story to implement:** STORY-009
**Story file:** `docs/stories/EPIC-02-ingestion/STORY-009.md`

---

## Last Completed Story

**STORY-008-BE — Text Quick-Capture (Backend, AC-1 to AC-5 only)** (2026-03-26)
`POST /v1/ingest/text` endpoint live. `TextIngestRequest` schema added. `ingest_text` ARQ task with plain-text chunking, OpenAI embedding, Qdrant upsert. `ErrorCode.TEXT_TOO_LONG` added. 70 tests passing, `make quality` clean. AC-6, AC-7, AC-8 (Omnibar UI) are pending Phase B Sprint 21 in ravenbase-web.

---

## Context for Next Session

STORY-008 backend (AC-1..AC-5) merged to main. story-counter is now 009 — the full STORY-008 row in epics.md will only flip to ✅ after the frontend session (AC-6..AC-8) in ravenbase-web completes in Phase B. Next up is STORY-009 (graph entity extraction — backend, staying in ravenbase-api).

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
