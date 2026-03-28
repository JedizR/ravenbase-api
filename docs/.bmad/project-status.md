# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** A — Backend (Sprints 1–17)
**Current sprint:** 16
**Status:** In progress — 16 of 37 stories complete

**Next story to implement:** STORY-028-BE
**Story file:** `docs/stories/EPIC-09-memory-intelligence/STORY-028.md`

---

## Last Completed Story

**STORY-026 — Conversational Memory Chat (Backend)** (2026-03-29)
Direct-SSE chat over user's memory base: `POST /v1/chat/message` streams Anthropic tokens via `EventSourceResponse` with session auto-creation, 6-message history window, Qdrant+Neo4j hybrid retrieval (RAGService reused), and credit deduction only after full response. `GET/DELETE /v1/chat/sessions` manage session lifecycle. Alembic migration creates `chat_sessions` table with JSONB messages column.

---

## Context for Next Session

STORY-026 merged to main. Conversational memory chat is fully wired: ChatService with `stream_turn()` async generator, AnthropicAdapter for RULE 1 compliance, bleach.clean() on responses per RULE 9. Backend sequence continues: 028-BE→029→[BACKEND GATE]→036-BE→037. STORY-028-BE is the AI chat context import helper endpoint.

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
