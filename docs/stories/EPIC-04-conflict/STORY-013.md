# STORY-013: Conflict API (List, Resolve, Undo)

**Epic:** EPIC-04 — Conflict Detection & Memory Inbox
**Priority:** P0
**Complexity:** Medium
**Depends on:** STORY-012

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-06-AC-1: POST /v1/conflicts/{id}/resolve accepts resolution_type in {accept_new, keep_old, custom}
- FR-06-AC-2: Resolution updates Conflict.status and propagates changes to Neo4j
- FR-06-AC-3: POST /v1/conflicts/{id}/undo reverts the resolution
- FR-06-AC-4: Resolved conflicts cannot be re-resolved without undoing first

## Component
COMP-02: GraphEngine

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 1: three-layer, RULE 2: tenant isolation)
> 2. `docs/architecture/03-api-contract.md` — `/v1/conflicts` endpoints full request/response spec
> 3. `docs/architecture/02-database-schema.md` — Conflict table, ConflictStatus constants
> 4. `docs/development/02-coding-standards.md` — three-layer architecture (route → service → adapter)

---

## User Story
As a user, I want API endpoints to list, resolve, and undo conflict resolutions so the UI can implement the Memory Inbox.

## Context
- API contract: `architecture/03-api-contract.md` — `/v1/conflicts` endpoints
- Data models: `architecture/02-database-schema.md` — Conflict table, ConflictStatus

## Acceptance Criteria
- [ ] AC-1: `GET /v1/conflicts?status=pending` returns paginated conflict list, newest first
- [ ] AC-2: `POST /v1/conflicts/{id}/resolve` with `action=ACCEPT_NEW`: marks new memory as `is_valid=true`, old as `is_valid=false`, creates SUPERSEDES Neo4j edge
- [ ] AC-3: `POST /v1/conflicts/{id}/resolve` with `action=KEEP_OLD`: marks conflict as resolved_keep_old, no graph changes
- [ ] AC-4: `POST /v1/conflicts/{id}/resolve` with `action=CUSTOM + custom_text`: sends custom text to Claude Haiku to generate graph mutation commands, applies them
- [ ] AC-5: `POST /v1/conflicts/{id}/undo`: reverses resolution only if within 30-second window (check `resolved_at`)
- [ ] AC-6: Resolving a conflict that doesn't belong to current user: returns `403`
- [ ] AC-7: Undo after 30-second window: returns `409 Conflict` with message explaining window expired
- [ ] AC-8: Response includes `graph_mutations` object showing what changed in Neo4j

## Technical Notes

### Files to Create
- `src/api/routes/conflict.py` — conflict CRUD endpoints
- `src/schemas/conflict.py` — ConflictResponse, ResolveRequest, ResolveResponse
- `tests/integration/api/test_conflict_api.py`

### Architecture Constraints
- Undo window: check `resolved_at + timedelta(seconds=30) > datetime.now(UTC)`
- Graph mutations must be atomic in Neo4j (use a transaction)
- Never allow resolving another user's conflict (check `user_id` before any mutation)
- Pagination: use `PaginatedResponse` from `src/schemas/common.py`

### Request / Response Schemas
```python
# src/schemas/conflict.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import str, Enum

class ResolveAction(str, Enum):
    ACCEPT_NEW = "ACCEPT_NEW"
    KEEP_OLD = "KEEP_OLD"
    CUSTOM = "CUSTOM"

class ResolveRequest(BaseModel):
    action: ResolveAction
    custom_text: str | None = None  # required when action=CUSTOM

class GraphMutations(BaseModel):
    edges_added: list[str] = []
    nodes_updated: list[str] = []

class ResolveResponse(BaseModel):
    conflict_id: UUID
    status: str
    graph_mutations: GraphMutations
```

### Undo Window Pattern
```python
from datetime import datetime, timedelta, UTC

def check_undo_window(conflict: Conflict) -> None:
    if conflict.resolved_at is None:
        raise HTTPException(status_code=400, detail="Conflict is not resolved")
    window_expires = conflict.resolved_at + timedelta(seconds=30)
    if datetime.now(UTC) > window_expires:
        raise HTTPException(
            status_code=409,
            detail={"code": "UNDO_WINDOW_EXPIRED", "message": "Undo window has expired (30 seconds)"},
        )
```

### SUPERSEDES Neo4j Pattern
```cypher
// ACCEPT_NEW: mark old memory invalid, add SUPERSEDES edge
MATCH (new:Memory {memory_id: $new_id, tenant_id: $tenant_id})
MATCH (old:Memory {memory_id: $old_id, tenant_id: $tenant_id})
MERGE (new)-[:SUPERSEDES]->(old)
SET old.is_valid = false, new.is_valid = true
```

## Definition of Done
- [ ] All 3 resolve actions work end-to-end
- [ ] Undo reverses the resolution within 30 seconds
- [ ] 409 returned after 30-second window
- [ ] 403 returned when resolving another user's conflict
- [ ] `graph_mutations` in response shows what changed
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Integration tests:
uv run pytest tests/integration/api/test_conflict_api.py -v

# Manual test flow:
TOKEN="your_clerk_token"
CONFLICT_ID="conflict-uuid"

# List pending conflicts:
curl http://localhost:8000/v1/conflicts?status=pending \
  -H "Authorization: Bearer ${TOKEN}"

# Resolve (accept new):
curl -X POST http://localhost:8000/v1/conflicts/${CONFLICT_ID}/resolve \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"action": "ACCEPT_NEW"}'

# Undo (within 30 seconds):
curl -X POST http://localhost:8000/v1/conflicts/${CONFLICT_ID}/undo \
  -H "Authorization: Bearer ${TOKEN}"
# Expected: 200 if within window, 409 if expired

# Quality:
make quality
```

**Passing result:** Conflicts list correctly. All 3 resolve actions produce correct DB + Neo4j state. Undo works within 30 seconds. 403 for cross-user access.

---

## Agent Implementation Brief

```
Implement STORY-013: Conflict API (List, Resolve, Undo).

Read first:
1. CLAUDE.md (architecture rules — RULE 1: three-layer, RULE 2: tenant isolation)
2. docs/architecture/03-api-contract.md (/v1/conflicts endpoints spec)
3. docs/architecture/02-database-schema.md (Conflict model, ConflictStatus)
4. docs/development/02-coding-standards.md (route → service → adapter pattern)
5. docs/stories/EPIC-04-conflict/STORY-013.md (this file)

Key constraints:
- Write ConflictResponse, ResolveRequest, ResolveResponse schemas FIRST (RULE 4)
- ALWAYS check conflict.user_id == current_user["user_id"] before any mutation
- Undo window: 30 seconds from resolved_at (use datetime.now(UTC))
- SUPERSEDES Neo4j edge must be in a transaction (atomic)
- Use PaginatedResponse from src/schemas/common.py for list endpoint

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# 1. Quality gate:
make quality && make test       # backend
npm run build && npm run test   # frontend (if applicable)

# 2. Commit:
git add -A && git commit -m "feat(ravenbase): STORY-013 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-013"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-013
git add docs/stories/epics.md && git commit -m "docs: mark STORY-013 complete"
```
