# STORY-003: Qdrant + Neo4j Initialization + Constraints

**Epic:** EPIC-01 — Foundation Infrastructure
**Priority:** P0
**Complexity:** Small
**Depends on:** STORY-001

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 2 tenant isolation and RULE 6 lazy imports)
> 2. `docs/architecture/02-database-schema.md` — Qdrant collection config + Neo4j node labels and constraints
> 3. `docs/development/02-coding-standards.md` — adapter pattern (BaseAdapter, lazy init, cleanup())
> 4. `docs/architecture/05-security-privacy.md` — `_tenant_filter()` implementation for Qdrant

---

## User Story
As a developer, I want Qdrant and Neo4j initialized with the correct collections/constraints so that all vector and graph operations have the right schema from day 1.

## Context
- Schema: `architecture/02-database-schema.md` — Qdrant collection config + Neo4j constraints
- Adapter pattern: `development/02-coding-standards.md` — `BaseAdapter` with lazy init and `cleanup()`
- Security pattern: `architecture/05-security-privacy.md` — `_tenant_filter()` and Cypher WHERE clause

## Acceptance Criteria
- [ ] AC-1: `QdrantAdapter` exists in `src/adapters/qdrant_adapter.py` and extends `BaseAdapter`
- [ ] AC-2: `Neo4jAdapter` exists in `src/adapters/neo4j_adapter.py` and extends `BaseAdapter`
- [ ] AC-3: `make setup-qdrant` creates the `ravenbase_chunks` collection with correct 1536-dim vector config + sparse BM25 vectors for hybrid search
- [ ] AC-4: `make setup-neo4j` creates all uniqueness constraints and indexes (user_id, profile_id, memory_id, concept_id)
- [ ] AC-5: Both adapters use lazy initialization — `__init__` does NOT open connection; connection opened on first method call
- [ ] AC-6: Both adapters are covered in `conftest.py` fixtures (mock versions) for unit tests
- [ ] AC-7: `/health` endpoint checks both Qdrant and Neo4j connectivity and reports individually

## Technical Notes

### Files to Create
- `src/adapters/qdrant_adapter.py` — with `search()`, `upsert()`, `delete_by_filter()`, `count()`, `_tenant_filter()` helper
- `src/adapters/neo4j_adapter.py` — with `run_query()`, `write_nodes()`, `write_relationships()`, `verify_connectivity()`
- `scripts/setup_qdrant.py` — creates `ravenbase_chunks` collection if not exists (idempotent)
- `scripts/setup_neo4j.py` — creates constraints and indexes (idempotent — uses `IF NOT EXISTS`)

### Files to Modify
- `src/api/routes/health.py` — add Qdrant + Neo4j connectivity checks
- `Makefile` — add `setup-qdrant`, `setup-neo4j` targets
- `tests/conftest.py` — add async fixtures: `mock_qdrant`, `mock_neo4j`

### Architecture Constraints
- Every Qdrant query MUST include `tenant_id` filter via `_tenant_filter()` helper — never call `search()` without it
- Every Neo4j Cypher MUST include `WHERE x.tenant_id = $tenant_id` — failure to do this is a security breach
- Adapter `__init__` must be fast — never open connections or load models in `__init__`
- All connections must be closed in `cleanup()` — test with context manager (`with adapter:`)
- Qdrant: use `qdrant_client.AsyncQdrantClient` (async) not the sync client

### Qdrant Adapter Pattern
```python
# src/adapters/qdrant_adapter.py
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.adapters.base import BaseAdapter
from src.core.config import settings

class QdrantAdapter(BaseAdapter):
    def __init__(self) -> None:
        self._client: AsyncQdrantClient | None = None  # Lazy init

    def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
        return self._client

    def _tenant_filter(self, tenant_id: str) -> Filter:
        """ALWAYS include this in every search/scroll/delete call."""
        return Filter(
            must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
        )

    async def search(
        self,
        query_vector: list[float],
        tenant_id: str,
        limit: int = 10,
        additional_filters: Filter | None = None,
    ) -> list:
        combined = self._tenant_filter(tenant_id)
        if additional_filters:
            combined.must.extend(additional_filters.must or [])
        return await self._get_client().search(
            collection_name="ravenbase_chunks",
            query_vector=query_vector,
            query_filter=combined,
            limit=limit,
        )

    def cleanup(self) -> None:
        if self._client:
            # AsyncQdrantClient manages its own connection pool
            self._client = None
```

### Qdrant Collection Config
```python
# scripts/setup_qdrant.py
from qdrant_client.models import VectorParams, Distance, SparseVectorParams, Modifier

COLLECTION_CONFIG = {
    "collection_name": "ravenbase_chunks",
    "vectors_config": VectorParams(size=1536, distance=Distance.COSINE),
    "sparse_vectors_config": {
        "bm25": SparseVectorParams(modifier=Modifier.IDF)  # Hybrid search
    },
    "on_disk_payload": True,  # Save memory for large payloads
}
```

### Neo4j Constraints (create in setup_neo4j.py)
```cypher
CREATE CONSTRAINT user_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE;
CREATE CONSTRAINT profile_unique IF NOT EXISTS FOR (p:SystemProfile) REQUIRE p.profile_id IS UNIQUE;
CREATE CONSTRAINT memory_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.memory_id IS UNIQUE;
CREATE CONSTRAINT concept_unique IF NOT EXISTS FOR (c:Concept) REQUIRE (c.tenant_id, c.name) IS UNIQUE;
CREATE INDEX concept_name_idx IF NOT EXISTS FOR (c:Concept) ON (c.name);
```

## Definition of Done
- [ ] `make setup-qdrant && make setup-neo4j` runs without errors (idempotent — can run multiple times)
- [ ] `curl localhost:8000/health` returns all 4 services green (postgres, redis, qdrant, neo4j)
- [ ] Unit tests: `tests/unit/adapters/test_qdrant_adapter.py` and `tests/unit/adapters/test_neo4j_adapter.py` pass
- [ ] `make quality` passes (0 errors)

## Testing This Story

```bash
# Setup the stores:
make setup-qdrant
make setup-neo4j

# Verify health endpoint shows all green:
curl http://localhost:8000/health | python3 -m json.tool
# Expected: {"status": "healthy", "checks": {"postgresql": "ok", "redis": "ok", "qdrant": "ok", "neo4j": "ok"}}

# Run adapter unit tests:
uv run pytest tests/unit/adapters/ -v

# Quality check:
make quality
```

**Passing result:** Health endpoint returns all 4 services "ok". Adapter tests pass. Qdrant collection `ravenbase_chunks` visible in Qdrant Cloud dashboard.

---

## Agent Implementation Brief

```
Implement STORY-003: Qdrant + Neo4j Initialization.

Read first:
1. CLAUDE.md (architecture rules — especially RULE 2 tenant isolation and RULE 5 lazy imports)
2. docs/architecture/02-database-schema.md (Qdrant collection config + Neo4j constraints section)
3. docs/development/02-coding-standards.md (adapter pattern — DoclingAdapter example to follow)
4. docs/architecture/05-security-privacy.md (_tenant_filter and Neo4j WHERE clause patterns)
5. docs/stories/EPIC-01-foundation/STORY-003.md (this file)

Key constraints:
- BaseAdapter.__init__ MUST be fast — no connections opened in __init__
- _tenant_filter() MUST be called in every Qdrant search/scroll/delete
- Every Neo4j Cypher MUST include WHERE x.tenant_id = $tenant_id
- Use AsyncQdrantClient (not sync)
- Scripts must be idempotent (use IF NOT EXISTS)

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
git add -A && git commit -m "feat(ravenbase): STORY-003 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-003"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-003
git add docs/stories/epics.md && git commit -m "docs: mark STORY-003 complete"
```
