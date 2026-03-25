# .bmad/ — BMAD Development Control Files

## story-counter.txt
Tracks the next story number. Increment after creating each story.

```bash
cat .bmad/story-counter.txt   # Check current (e.g., "001")
echo "002" > .bmad/story-counter.txt  # Increment after use
```

## BMAD Skills
Install from: https://github.com/aj-geddes/claude-code-bmad-skills

Available commands in Claude Code after installation:
```
/bmad:architecture    # System Architect reviews design before coding
/bmad:brainstorm      # Explore approaches and trade-offs
/bmad:create-story    # Generate a story document with AI help
/bmad:dev-story STORY-XXX  # Implement a story with Developer agent context
```

## Usage Pattern (Solo Dev)
1. Pick next story from docs/stories/epics.md
2. Read the story file
3. Run: `/bmad:dev-story STORY-XXX`
   OR: paste the Agent Implementation Brief from docs/stories/README.md
4. Review plan, approve, implement
5. make quality && make test
6. Mark ACs as complete in story file
7. Increment story-counter.txt
8. Commit + PR
