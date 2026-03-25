# Stories — README & Template

> **Cross-references:** `docs/README.md` (workflow) | `stories/epics.md` (all stories list)

---

## What Is a Story?

A story is the **atomic unit of development**. It answers:
- What feature is being built (user story)?
- What must be true when it's done (acceptance criteria)?
- What existing code does it build on (context)?
- What files will be created or modified (technical notes)?

**Every story maps to one feature branch and one PR.** Stories are small enough to complete in one Claude Code session (2-6 hours of agent time).

---

## Story Template

Copy this for every new story:

```markdown
# STORY-XXX: Feature Name

**Epic:** EPIC-0X — Epic Name
**Priority:** P0 | P1 | P2
**Estimated complexity:** Small (1-2h) | Medium (3-4h) | Large (5-6h)
**Depends on:** STORY-YYY (if any prerequisite)

---

## User Story
As a [persona], I want [action] so that [benefit].

## Context
[What already exists that this builds on. Reference specific files agents should read.]

Example:
- Service pattern: see `src/services/ingestion_service.py`
- Adapter pattern: see `src/adapters/docling_adapter.py`
- DB models: see `architecture/02-database-schema.md` — Source table

## Acceptance Criteria
- [ ] AC-1: Specific, testable, observable condition
- [ ] AC-2: Another condition (maps to a test case)
- [ ] AC-3: Error case: what happens when X fails
- [ ] AC-4: Performance: operation completes within Xms/Xs

## Technical Notes

### Files to Create
- `src/services/my_service.py` — extends BaseService
- `tests/unit/services/test_my_service.py`

### Files to Modify
- `src/api/routes/ingest.py` — add new endpoint
- `alembic/versions/xxx_add_table.py` — migration

### Do NOT Create
- New dependencies without listing them here first
- New database tables (extend existing with JSONB if possible)

### Architecture Constraints
- Must follow 3-layer: route → service → adapter
- All DB queries must include WHERE user_id = ?
- Job must be queued to ARQ if duration > 2s

## Definition of Done
- [ ] All acceptance criteria have passing tests
- [ ] `make quality` passes (0 errors)
- [ ] `make test` passes
- [ ] PR merged to main with CI green
```

---

## Agent Implementation Brief (Copy-Paste to Claude Code)

```
Implement STORY-XXX: [Feature Name]

Read: docs/stories/EPIC-0X/STORY-XXX.md for requirements.
Read: docs/CLAUDE.md for architecture rules.
Read: docs/architecture/02-database-schema.md for data models.

Architecture constraints:
- Three-layer: route → service → adapter
- All services extend BaseService with cleanup()
- All adapters extend BaseAdapter with cleanup()
- Heavy imports lazy (inside function body, # noqa: PLC0415)
- asyncio.get_running_loop() not get_event_loop()
- structlog not print()
- Tenant isolation: every DB/Qdrant/Neo4j query must filter by tenant_id

Protocol:
1. Show me implementation plan first (files to create/modify, approach)
2. Write schemas/models first
3. Write tests second
4. Implement third
5. Run make quality && make test

Do NOT start implementing yet. Show plan first.
```

---

## Story Lifecycle

```
DRAFT     → Story is written but not yet started
READY     → Story is approved and ready for implementation
IN_PROGRESS → Active Claude Code session
IN_REVIEW → PR open, CI running
DONE      → PR merged, CI green, story marked complete
```

Update the checkboxes in each story file as you complete acceptance criteria.

---

## Story Counter

The next story number is tracked in `.bmad/story-counter.txt`.

```bash
cat .bmad/story-counter.txt     # Check current (e.g., "026")
echo "027" > .bmad/story-counter.txt  # Increment after use
```
