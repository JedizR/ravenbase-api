# Ravenbase — Automated Development Loop

This document defines the exact repeating loop for every story implementation.
Claude Code agents executing stories must follow this loop without deviation.
The loop is designed to be self-contained: an agent starting fresh can read this
document and implement stories correctly with no additional context.

**Cross-repo stories** (STORY-018, STORY-028, STORY-036, and split FE/BE stories like
STORY-007 and STORY-008) require two separate Claude Code sessions — one in
`ravenbase-api` using the **Backend Agent Brief**, then one in `ravenbase-web` using
the **Frontend Agent Brief**. Both sessions follow this same loop independently.
The backend session must complete and push before the frontend session begins.
See `docs/PARALLEL_DEV_GUIDE.md` for the full list of cross-repo stories.

---

## The Loop (one iteration = one story)

```
┌─────────────────────────────────────────────────────────────────┐
│                    STORY EXECUTION LOOP                         │
│                                                                 │
│  START ─────────────────────────────────────────────────────►   │
│                                                                 │
│  1. READ                                                        │
│     Read CLAUDE.md (root) completely                            │
│     Read the story file completely                              │
│     Read all files listed in "Before You Start"                 │
│                                                                 │
│  2. PLAN                                                        │
│     Output your implementation plan:                            │
│     - Files to create (with exact paths)                        │
│     - Files to modify (with what changes)                       │
│     - How each AC maps to code                                  │
│     Stop. Wait for explicit approval.                           │
│                                                                 │
│  3. IMPLEMENT (after approval only)                             │
│     Order: schemas/models → tests → implementation              │
│     Never skip tests. Never implement before schemas.           │
│                                                                 │
│  4. QUALITY GATE (automated — run these exact commands)         │
│     Backend:                                                    │
│       make quality        ← must show 0 errors                  │
│       make test           ← must show 0 failures                │
│     Frontend:                                                   │
│       npm run build       ← must show 0 TypeScript errors       │
│       npm run test        ← must show 0 failures                │
│                                                                 │
│  5. VERIFY                                                      │
│     Run the "Testing This Story" commands from the story file   │
│     Confirm expected output matches actual output               │
│     Check each AC checkbox: confirm it is met                   │
│                                                                 │
│  6. COMMIT                                                      │
│     git add -A                                                  │
│     git commit -m "feat(ravenbase): STORY-XXX short description"│
│     git push                                                    │
│                                                                 │
│  7. POST-STORY ACTIONS (backend stories only)                   │
│     If story added or changed any API endpoint:                 │
│     → cd ravenbase-web/                                         │
│     → npm run generate-client                                   │
│     → git add src/lib/api-client/                               │
│     → git commit -m "chore: regenerate client after STORY-XXX"  │
│     → git push                                                  │
│                                                                 │
│  8. MARK COMPLETE + UPDATE STATE                                │
│     In docs/stories/epics.md:                                   │
│     → Change story status from 🔲 to ✅                          │
│     In docs/.bmad/project-status.md:                            │
│     → Update current sprint, next story, last completed story   │
│     In docs/.bmad/story-counter.txt:                            │
│     → Set to the next backend story ID in the sequence.          │
│       Backend: 001→002→…→009→010→012→013→015→016→018-BE          │
│       →023→024→025→026→028-BE→029→[GATE]→036-BE→037             │
│       Frontend-only stories (011,014,017,etc) are skipped here.  │
│                                                                 │
│  9. JOURNAL ENTRY (mandatory — never skip)                      │
│     Open docs/.bmad/journal.md                                  │
│     Append one entry under the correct Sprint section           │
│     Fill ALL 6 fields: what was built, key decisions,           │
│     gotchas, tech debt, quality gate result, commit hash        │
│     Update the Project Stats table at the top of the file       │
│     git add docs/stories/epics.md \                             │
│             docs/.bmad/project-status.md \                      │
│             docs/.bmad/journal.md                               │
│     git commit -m "docs: mark STORY-XXX complete"               │
│     git push                                                    │
│                                                                 │
│  ─────────────────────────────────────────────────────── END    │
│  Pick next story from docs/stories/epics.md (first 🔲 row)      │
│  Return to START                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pre-Story Checklist (copy this into your first message)

Every Claude Code session implementing a story must begin with:

> **Before pasting the brief:** Read `.bmad/project-status.md` to confirm you are working
> on the correct next story. Takes 10 seconds and prevents working on the wrong thing.

```
I am implementing STORY-XXX: [title].

Before writing any code, I will:
1. Read CLAUDE.md completely (I must not assume I remember it)
2. Read docs/.bmad/project-status.md (confirm I have the right story)
3. Read the last 2–3 entries in docs/.bmad/journal.md (recent decisions + gotchas)
4. Read docs/stories/EPIC-XX/STORY-XXX.md completely
5. Read each file listed in the "Before You Start" box
6. Output my implementation plan
7. Stop and wait for your approval before implementing

I will NOT write any code until you approve my plan.
```

---

## Post-Story Commit Template

```bash
# Backend story commit:
git add -A
git commit -m "feat(ravenbase): STORY-XXX brief description of what was implemented"
git push origin main

# After any backend story that added/changed endpoints:
cd ../ravenbase-web
npm run generate-client   # requires API server running at localhost:8000
git add src/lib/api-client/
git commit -m "chore: regenerate API client after STORY-XXX"
git push origin main
cd ../ravenbase-api

# Mark story complete + update journal:
# 1. Edit docs/stories/epics.md → change 🔲 to ✅ for STORY-XXX
# 2. Update docs/.bmad/project-status.md → current sprint, next story
# 3. Append entry to docs/.bmad/journal.md → all 6 fields + stats table
git add docs/stories/epics.md docs/.bmad/project-status.md docs/.bmad/journal.md
git commit -m "docs: mark STORY-XXX complete"
git push origin main
```

---

## Quality Gate Rules

**Never skip. Never bypass. Never "I'll fix it in the next story."**

```
make quality MUST show:
  0 ruff errors
  0 pyright errors

make test MUST show:
  0 failed tests
  0 errors
  Coverage >= 70%

npm run build MUST show:
  Compiled successfully
  0 TypeScript errors
  0 warnings (treat warnings as errors)
```

If quality gate fails:
1. Do NOT commit failing code
2. Fix the failure before proceeding
3. Re-run quality gate
4. Only commit when gate is clean

---

## Stuck? Escalation Protocol

If an implementation is stuck for more than one iteration:

```
Tell the developer:
"I am stuck on [specific problem]. Here is what I have tried:
1. [approach 1] — result: [what happened]
2. [approach 2] — result: [what happened]
I need guidance on: [specific question]"
```

Never silently produce broken code. Never assume a workaround is acceptable.
Ask first.

---

## The generate-client Trigger

Run `npm run generate-client` (in ravenbase-web) after any backend story that:
- Adds a new endpoint (any new `@router.post/get/delete`)
- Changes a request body schema
- Changes a response schema
- Adds a new field to any Pydantic response model

**EPIC-09 stories that require client regeneration:**
- After STORY-026 (chat endpoints — POST /v1/chat/message, GET /v1/chat/sessions, etc.)
- After STORY-028-BE (import prompt — GET /v1/ingest/import-prompt)
- After STORY-029 (graph query — POST /v1/graph/query)
- STORY-027, STORY-028-FE, STORY-030 are frontend-only — no client regen needed

Do NOT run it after backend stories that only:
- Add background worker tasks (no new endpoints)
- Fix bugs in existing endpoints without changing schemas
- Add indexes or migrations without changing the API

When in doubt, run it. It is idempotent and takes 5 seconds.
