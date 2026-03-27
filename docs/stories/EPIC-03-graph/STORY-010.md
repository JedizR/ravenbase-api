# STORY-010: Graph API Endpoints

**Epic:** EPIC-03 — Knowledge Graph Layer
**Priority:** P0
**Complexity:** Medium
**Depends on:** STORY-009
**Type:** Backend
**Repo:** ravenbase-api

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 2 tenant isolation)
> 2. `docs/architecture/03-api-contract.md` — `/v1/graph/nodes` and `/v1/graph/neighborhood/{node_id}` exact request/response specs
> 3. `docs/architecture/02-database-schema.md` — Neo4j schema: node labels, relationship types, Key Cypher Queries section
> 4. `docs/development/02-coding-standards.md` — three-layer architecture (route → service → adapter)

---

## User Story
As a developer, I want REST endpoints that return graph data so the Graph Explorer UI can visualize the knowledge graph.

## Context
- API contract: `architecture/03-api-contract.md` — `/v1/graph/nodes`, `/v1/graph/neighborhood/{node_id}`
- Neo4j queries: `architecture/02-database-schema.md` — Key Cypher Queries section
- Graph service: STORY-009 created `src/services/graph_service.py` and `src/adapters/neo4j_adapter.py`

## Acceptance Criteria
- [ ] AC-1: `GET /v1/graph/nodes?profile_id=&node_types=&limit=200` returns nodes + edges for Graph Explorer
- [ ] AC-2: Response shape: `{nodes: [{id, label, type, properties, memory_count}], edges: [{source, target, type, properties}]}`
- [ ] AC-3: `GET /v1/graph/neighborhood/{node_id}?hops=2&limit=50` returns N-hop subgraph centered on that node
- [ ] AC-4: All queries filter by `tenant_id` from JWT (NEVER accept tenant_id in request body or query params)
- [ ] AC-5: Profile filter: if `profile_id` provided, only return nodes linked to that profile via `HAS_MEMORY` edges
- [ ] AC-6: Response time < 500ms for graphs up to 500 nodes (Neo4j query uses indexes created in STORY-003)
- [ ] AC-7: Empty graph (new user): returns `{nodes: [], edges: []}` — never a 404

## Technical Notes

### Files to Create
- `src/api/routes/graph.py` — graph endpoints with `require_user` dependency
- `src/schemas/graph.py` — `GraphNode`, `GraphEdge`, `GraphResponse` Pydantic schemas
- `tests/integration/api/test_graph_endpoints.py` — endpoint tests with mocked Neo4j

### Files to Modify
- `src/api/main.py` — include `graph` router
- `src/services/graph_service.py` — add `get_nodes_for_explorer()` and `get_neighborhood()` methods

### Architecture Constraints
- Route must call `graph_service`, NOT call `neo4j_adapter` directly
- `tenant_id` comes exclusively from `require_user` dependency — never from request params
- Profile filter is optional — if not provided, return all nodes for tenant
- Neighborhood query MUST include `tenant_id` in Cypher WHERE clause even when filtering by `node_id`
- Response schemas defined in `src/schemas/graph.py` before implementation

### Cypher Queries for These Endpoints
```cypher
-- GET /v1/graph/nodes
MATCH (n)
WHERE n.tenant_id = $tenant_id
  AND ($profile_id IS NULL OR (n)-[:HAS_MEMORY]-(:SystemProfile {profile_id: $profile_id}))
WITH n
OPTIONAL MATCH (n)-[r]-(m)
WHERE m.tenant_id = $tenant_id
RETURN n, r, m LIMIT $limit

-- GET /v1/graph/neighborhood/{node_id}
MATCH (start {concept_id: $node_id, tenant_id: $tenant_id})
MATCH path = (start)-[*1..$hops]-(neighbor)
WHERE ALL(x IN nodes(path) WHERE x.tenant_id = $tenant_id)
RETURN nodes(path), relationships(path) LIMIT $limit
```

### Response Schema
```python
# src/schemas/graph.py
from pydantic import BaseModel
from typing import Any

class GraphNode(BaseModel):
    id: str
    label: str
    type: str          # "concept" | "memory" | "source" | "conflict"
    properties: dict[str, Any]
    memory_count: int = 0

class GraphEdge(BaseModel):
    source: str
    target: str
    type: str          # "RELATES_TO" | "EXTRACTED_FROM" | "CONTRADICTS" | "SUPERSEDES"
    properties: dict[str, Any] = {}

class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
```

## Definition of Done
- [ ] `GET /v1/graph/nodes` returns `{nodes: [], edges: []}` for empty graph (not 404)
- [ ] `GET /v1/graph/neighborhood/{node_id}` returns correct subgraph
- [ ] All queries filter by `tenant_id` (verified by integration test with two different users)
- [ ] Integration tests pass: `tests/integration/api/test_graph_endpoints.py`
- [ ] `make quality` passes (0 errors)
- [ ] `npm run generate-client` in `ravenbase-web/` regenerates TypeScript client successfully

## Testing This Story

```bash
# Run graph endpoint tests:
uv run pytest tests/integration/api/test_graph_endpoints.py -v

# Manual test with empty graph:
curl -X GET "http://localhost:8000/v1/graph/nodes" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Expected: {"nodes": [], "edges": []}

# Quality:
make quality

# After passing, regenerate frontend client:
cd ~/ravenbase/ravenbase-web && npm run generate-client
```

**Passing result:** Graph endpoints return correct data. Tenant isolation test passes. `npm run generate-client` succeeds in the web repo.

---

## Agent Implementation Brief

```
Implement STORY-010: Graph API Endpoints.

Read first:
1. CLAUDE.md (architecture rules — RULE 2 tenant isolation is critical here)
2. docs/architecture/03-api-contract.md (exact response shapes for /v1/graph/* endpoints)
3. docs/architecture/02-database-schema.md (Key Cypher Queries section + relationship types)
4. docs/development/02-coding-standards.md (three-layer: route → service → adapter)
5. docs/stories/EPIC-03-graph/STORY-010.md (this file)

Key constraints:
- Write GraphNode, GraphEdge, GraphResponse Pydantic schemas FIRST
- Write integration tests SECOND
- tenant_id from JWT ONLY — never from request params
- Empty graph returns {nodes: [], edges: []} not 404
- Route calls graph_service.get_nodes_for_explorer(), not neo4j_adapter directly

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
git add -A && git commit -m "feat(ravenbase): STORY-010 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-010"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-010
git add docs/stories/epics.md && git commit -m "docs: mark STORY-010 complete"
```
