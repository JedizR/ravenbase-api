# STORY-015: Hybrid Retrieval Service

**Epic:** EPIC-05 — Meta-Document Generation
**Priority:** P0
**Complexity:** Large
**Depends on:** STORY-009

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 2: tenant isolation, RULE 4: schemas first)
> 2. `docs/architecture/00-system-overview.md` — Meta-Document generation data flow
> 3. `docs/architecture/03-api-contract.md` — `/v1/metadoc/generate` request/response spec
> 4. `docs/architecture/02-database-schema.md` — Qdrant payload schema, Neo4j Memory node properties
> 5. `docs/development/02-coding-standards.md` — service + adapter pattern

---

## User Story
As a developer, I want a retrieval service that combines Qdrant semantic search with Neo4j graph traversal so Meta-Documents can be grounded in both meaning and structure.

## Context
- Data flow: `architecture/00-system-overview.md` — Meta-Document generation flow
- API contract: `architecture/03-api-contract.md` — `/v1/metadoc/generate`

## Acceptance Criteria
- [ ] AC-1: `RAGService.retrieve()` accepts `{prompt, profile_id, tenant_id, limit}` and returns ranked chunks
- [ ] AC-2: Phase 1 — Qdrant kNN search: semantic search with tenant + profile filter, returns top-30 candidates
- [ ] AC-3: Phase 2 — Neo4j traversal: Cypher query to find Memory nodes related to extracted concepts, returns temporally ordered results
- [ ] AC-4: Phase 3 — Re-ranking: `final_score = (semantic_score × 0.6) + (recency_weight × 0.3) + (profile_match × 0.1)`
- [ ] AC-5: Returns top-N unique chunks (deduped by content hash) with attribution (source_id, memory_id)
- [ ] AC-6: Empty result (no relevant memories): returns empty list, does not hallucinate
- [ ] AC-7: Retrieval completes within 3 seconds for a user with 10,000 chunks

## Technical Notes

### Files to Create
- `src/services/rag_service.py` — `retrieve()` method with 3-phase pipeline
- `tests/unit/services/test_rag_service.py` — unit tests with mocked Qdrant + Neo4j
- `tests/integration/services/test_rag_retrieval.py` — with seeded Qdrant + Neo4j data

### Architecture Constraints
- RAGService extends BaseService — inject adapters via constructor (not instantiated inside)
- Qdrant query MUST include `tenant_id` filter (never search without it)
- Neo4j query MUST include `tenant_id` in WHERE clause
- Re-ranking is pure Python math — no additional ML model needed

### RetrievedChunk Schema
```python
# src/schemas/rag.py
from pydantic import BaseModel
from uuid import UUID

class RetrievedChunk(BaseModel):
    chunk_id: str
    content: str
    source_id: UUID
    memory_id: UUID | None = None
    final_score: float
    semantic_score: float
    recency_weight: float
    page_number: int | None = None
```

### Three-Phase Retrieval Pattern
```python
# src/services/rag_service.py
class RAGService(BaseService):
    def __init__(
        self,
        qdrant: QdrantAdapter | None = None,
        neo4j: Neo4jAdapter | None = None,
        openai: OpenAIAdapter | None = None,
    ) -> None:
        self._qdrant = qdrant
        self._neo4j = neo4j
        self._openai = openai

    async def retrieve(
        self,
        prompt: str,
        profile_id: str,
        tenant_id: str,
        limit: int = 10,
    ) -> list[RetrievedChunk]:
        log = logger.bind(tenant_id=tenant_id, profile_id=profile_id)

        # Phase 1: Qdrant semantic search
        prompt_embedding = await self._get_openai().embed(prompt)
        qdrant_results = await self._get_qdrant().search(
            query_vector=prompt_embedding,
            tenant_id=tenant_id,
            profile_id=profile_id,
            limit=30,
        )
        log.info("rag.qdrant_results", count=len(qdrant_results))

        # Phase 2: Neo4j graph traversal for related memories
        concept_names = extract_concepts(prompt)  # simple noun extraction
        neo4j_memories = await self._get_neo4j().find_memories_by_concepts(
            concept_names=concept_names,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        log.info("rag.neo4j_results", count=len(neo4j_memories))

        # Phase 3: Re-rank and deduplicate
        combined = merge_and_deduplicate(qdrant_results, neo4j_memories)
        ranked = rerank(combined)  # applies scoring formula
        return ranked[:limit]
```

### Re-ranking Formula
```python
def rerank(chunks: list[dict]) -> list[RetrievedChunk]:
    now = datetime.now(UTC)
    result = []
    for chunk in chunks:
        age_days = (now - chunk["created_at"]).days
        recency_weight = 1.0 / (1.0 + age_days / 30)  # decays over months
        profile_match = 1.0 if chunk.get("profile_id") else 0.5

        final_score = (
            chunk["semantic_score"] * 0.6
            + recency_weight * 0.3
            + profile_match * 0.1
        )
        result.append(RetrievedChunk(**chunk, final_score=final_score, recency_weight=recency_weight))
    return sorted(result, key=lambda c: c.final_score, reverse=True)
```

## Definition of Done
- [ ] `retrieve()` returns correctly ranked chunks within 3 seconds for 10,000 chunks
- [ ] Re-ranking formula applied correctly (semantic × 0.6 + recency × 0.3 + profile × 0.1)
- [ ] Qdrant and Neo4j results merged and deduplicated
- [ ] Empty prompt returns empty list (no error)
- [ ] Unit tests pass with mocked adapters
- [ ] Integration tests pass with seeded data
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Unit tests (fast — mocked adapters):
uv run pytest tests/unit/services/test_rag_service.py -v

# Integration tests (requires Qdrant + Neo4j running with seeded data):
uv run pytest tests/integration/services/test_rag_retrieval.py -v

# Performance test (10,000 chunks):
uv run pytest tests/integration/services/test_rag_retrieval.py::test_retrieval_performance -v
# Expected: < 3 seconds

# Quality:
make quality
```

**Passing result:** `retrieve()` returns top-N ranked chunks with attribution. Performance < 3 seconds for 10,000 chunks. Empty result returns `[]`.

---

## Agent Implementation Brief

```
Implement STORY-015: Hybrid Retrieval Service.

Read first:
1. CLAUDE.md (architecture rules — RULE 2: tenant isolation, RULE 4: schemas first)
2. docs/architecture/00-system-overview.md (Meta-Document generation data flow)
3. docs/architecture/02-database-schema.md (Qdrant payload schema, Neo4j Memory properties)
4. docs/development/02-coding-standards.md (BaseService pattern, adapter injection)
5. docs/stories/EPIC-05-metadoc/STORY-015.md (this file)

Key constraints:
- Write RetrievedChunk Pydantic schema FIRST (before service implementation)
- RAGService extends BaseService — adapters injected in constructor
- Qdrant MUST have tenant_id filter in every search call
- Neo4j MUST have tenant_id in WHERE clause
- Re-ranking formula: semantic_score×0.6 + recency_weight×0.3 + profile_match×0.1
- Deduplication by content hash (not chunk_id — same content may appear in both results)

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
git add -A && git commit -m "feat(ravenbase): STORY-015 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-015"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-015
git add docs/stories/epics.md && git commit -m "docs: mark STORY-015 complete"
```
