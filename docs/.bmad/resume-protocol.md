# Ravenbase — Session Resume Protocol

Use this when a story is marked 🔄 IN_PROGRESS and you are starting a new Claude Code
session to continue it. A story is IN_PROGRESS when work started but was not completed
before the session ended.

---

## Step 1 — Understand current state (before opening Claude Code)

1. Read `.bmad/project-status.md` — note the current story and any session notes
2. Read the last 2–3 entries in `.bmad/journal.md` — understand recent decisions
   and gotchas that may affect the story you are resuming
3. Read the story file — note which ACs have `[x]` (done) vs `[ ]` (remaining)
4. Scan the relevant source files in the repo — understand what was already implemented

---

## Step 2 — Resume message (paste this into Claude Code)

```
I am resuming STORY-XXX: [title]. It is partially complete.

Before anything else, read:
1. CLAUDE.md (architecture rules)
2. docs/stories/EPIC-XX/STORY-XXX.md (the story — note which ACs are already checked)
3. [list the specific files that were created so far]

After reading, tell me:
- Which acceptance criteria are already met by the existing code
- Which acceptance criteria are NOT yet met
- Your plan to complete only the remaining work

Do NOT re-implement anything that already exists.
Do NOT start implementing yet. Show me your completion plan first.
```

---

## Step 3 — Approve the completion plan

Review Claude Code's assessment. If it correctly identifies what's done and what remains,
approve it. If it misses something or proposes re-doing existing work, redirect it:

> "AC-X is already implemented in `src/path/to/file.py`. Skip it and focus on AC-Y."

---

## Step 4 — Complete the story normally

Once the remaining ACs are implemented, run the standard quality gate and commit sequence
from `DEVELOPMENT_LOOP.md`. Mark the story ✅ in `docs/stories/epics.md`.

---

## When NOT to use this protocol

If you decide to discard the partial work and restart the story cleanly:
1. Delete the files that were created for the story
2. Change story status back to 🔲 in `docs/stories/epics.md`
3. Start a fresh session with the standard Agent Implementation Brief
