# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 12
**Status:** In progress — 12 of 37 stories complete

**Next story to implement:** STORY-018-BE
**Story file:** `docs/stories/EPIC-05-metadoc/STORY-018.md`

---

## Last Completed Story

**STORY-016 — Meta-Doc Generation Worker + Streaming** (2026-03-28)
End-to-end Meta-Document pipeline: `POST /v1/metadoc/generate` (credit check → ARQ enqueue → 202), `GET /v1/metadoc/stream/{job_id}` (SSE re-stream from Redis pub/sub), ARQ worker `generate_meta_document` (RAGService retrieval → Presidio PII masking → Anthropic streaming → bleach sanitization → PostgreSQL save → Neo4j CONTAINS edges → credit deduction). 182 tests passing, `make quality` clean.

---

## Context for Next Session

STORY-016 merged to main. Meta-Doc generation pipeline is complete. Key patterns: credits checked (402) before ARQ enqueue, deducted only after successful generation (AC-9). SSE auth via `?token=` query param (EventSource can't set headers). `verify_token_query_param` now returns 401 (not 422) for missing token. STORY-017 is frontend-only (Workstation UI) — skip to STORY-018-BE.

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
