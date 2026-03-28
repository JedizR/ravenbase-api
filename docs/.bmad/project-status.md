# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 15
**Status:** In progress — 16 of 37 stories complete

**Next story to implement:** STORY-026
**Story file:** `docs/stories/EPIC-09-memory-intelligence/STORY-026.md`

---

## Last Completed Story

**STORY-025 — PII Masking in Production + Presidio Config** (2026-03-28)
`PresidioAdapter.mask_text()` with async Redis-backed deterministic entity map (Entity_NNN aliases consistent across chunks). Lazy import of presidio libraries (RULE 6). `generate_meta_document` worker calls `mask_text` per chunk when `ENABLE_PII_MASKING=true`, deletes Redis key in `finally` block. 7 tests added. Tests passing, `make quality` clean.

---

## Context for Next Session

STORY-025 merged to main. PII masking is fully wired into the metadoc pipeline — Presidio analyzer+anonymizer lazy-loaded, Redis entity map ensures cross-chunk consistency, cleanup guaranteed via `finally`. Backend sequence continues: 026→028-BE→029→[BACKEND GATE]→036-BE→037. STORY-026 is Conversational Memory Chat (backend).

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
