# RetrievalEngine

> **Component ID:** BE-COMP-03
> **Epic:** EPIC-05 — Meta-Document Generation
> **Stories:** STORY-015, STORY-016 (retrieval portion)
> **Type:** Backend

---

## Purpose

The RetrievalEngine is the context-grounding layer used by every LLM operation in Ravenbase. `RAGService.retrieve()` implements hybrid retrieval: Qdrant semantic search (kNN) + Neo4j graph-neighbor traversal + re-ranking by weighted formula. Both the Meta-Document generator and the Memory Chat system call this service to build grounded context before sending anything to an LLM.

---

## User Journey

The retrieval pipeline is invisible to users — it runs automatically before any LLM call:

1. User triggers a generation (Meta-Doc, Chat message)
2. `GenerationEngine` calls `RAGService.retrieve(prompt, profile_id, tenant_id, limit)`
3. Phase 1: Qdrant kNN search returns top-30 semantically similar chunks
4. Phase 2: Neo4j Cypher traversal finds related Memory nodes via concept edges
5. Phase 3: Results merged, deduplicated by content hash, re-ranked:
   `final_score = (semantic_score × 0.6) + (recency_weight × 0.3) + (profile_match × 0.1)`
6. Top-N unique chunks returned with attribution (`source_id`, `memory_id`, page number)
7. These chunks become the LLM's context window — grounding the AI's output in real user data
8. If no relevant memories exist: returns `[]` — LLM told "no relevant memories found"

---

## Admin Bypass

No credits consumed by retrieval — admin bypass not needed.

Retrieval runs identically for admin and regular users. Tenant isolation (`tenant_id` filtering) applies to all users including admins — this is a security invariant, not a feature to bypass.

---

## Known Bugs / Current State

No known bugs in RetrievalEngine. Implementation is complete per STORY-015.

**Verify before relying on retrieval:**
- All Qdrant queries include `tenant_id` filter (security check)
- All Neo4j queries use `WHERE n.tenant_id = $tenant_id` (never string-interpolated)
- Profile scoping: `profile_id` filter applied when provided
- Performance: must complete in < 3 seconds for 10,000-chunk corpus

---

## Acceptance Criteria

- [ ] `RAGService.retrieve()` returns `list[RetrievedChunk]` sorted by `final_score`
- [ ] Re-ranking formula: `semantic×0.6 + recency×0.3 + profile×0.1`
- [ ] Qdrant search scoped to `tenant_id` — no cross-tenant data
- [ ] Neo4j traversal scoped to `tenant_id` — no cross-tenant nodes
- [ ] Deduplication: same content appearing in both Qdrant + Neo4j results appears once
- [ ] Empty result returns `[]` — no error, no hallucination
- [ ] Performance: < 3 seconds for 10,000-chunk corpus
- [ ] Each returned chunk includes `source_id`, `memory_id`, page number for citation

---

## Cross-references

- `BE-COMP-04-GenerationEngine.md` — primary consumer of `RAGService.retrieve()`
- `BE-COMP-01-IngestionPipeline.md` — creates the chunks that retrieval searches
- `BE-COMP-02-GraphEngine.md` — Neo4j graph that retrieval traverses
- `docs/architecture/03-api-contract.md` — no direct HTTP endpoints (internal service)

---

## Goal

The RetrievalEngine provides hybrid retrieval combining Qdrant semantic search with Neo4j graph-neighbor boosting. It is the foundation for both Meta-Document generation and Conversational Memory Chat — any component that needs to ground LLM output in the user's knowledge base uses `RAGService.retrieve()`.

---

## Product Requirements

1. **Hybrid Retrieval:** `RAGService.retrieve()` combines three phases: (1) Qdrant kNN semantic search, (2) Neo4j Cypher traversal for related memories, (3) re-ranking by `final_score = (semantic_score × 0.6) + (recency_weight × 0.3) + (profile_match × 0.1)`.

2. **Tenant Isolation:** All Qdrant and Neo4j queries include `tenant_id` filter. The service never returns data belonging to another tenant.

3. **Profile Scoping:** Optional `profile_id` parameter further scopes retrieval to memories linked to a specific System Profile via `HAS_MEMORY` edges.

4. **Top-30 Candidates:** Qdrant semantic search returns top-30 candidates, which are then merged with Neo4j graph-neighbor results and re-ranked.

5. **Deduplication:** Results are deduplicated by content hash — the same content appearing in both Qdrant and Neo4j results appears only once.

6. **Attribution:** Each returned chunk includes `chunk_id`, `source_id`, `memory_id`, and page number for citation.

7. **Empty Result Handling:** If no relevant memories exist, returns an empty list — never hallucinates or fabricates content.

8. **Performance SLA:** Retrieval completes within 3 seconds for a user with 10,000 chunks.

9. **Meta-Doc Integration:** `RAGService.retrieve()` is called by the `generate_meta_document` ARQ task to populate context before LLM synthesis.

10. **Chat Integration:** `RAGService.retrieve()` is called by the chat service with `limit=8` (fewer chunks than Meta-Doc since chat is more focused).

---

## Criteria and Tests

| Criterion | Test |
|---|---|
| RAGService.retrieve() returns ranked chunks | Call with prompt → returns list of RetrievedChunk sorted by final_score |
| Re-ranking formula applied | Verify semantic×0.6 + recency×0.3 + profile×0.1 |
| Qdrant search tenant-scoped | Call with tenant A → verify no tenant B data |
| Neo4j traversal tenant-scoped | Call with tenant A → verify no tenant B nodes |
| Deduplication works | Same content in Qdrant + Neo4j results → appears once |
| Empty result returns [] | Call with gibberish prompt → returns [] |
| Performance < 3s for 10K chunks | uv run pytest test_retrieval_performance → < 3s |
| Hybrid merge works | Qdrant-only vs Neo4j-only vs both → correct merged result |

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-015](../stories/EPIC-05-metadoc/STORY-015.md) | Hybrid Retrieval Service | Backend | 3-phase RAG: Qdrant → Neo4j → re-rank |
| [STORY-016](../stories/EPIC-05-metadoc/STORY-016.md) | Meta-Doc Generation Worker | Backend | SSE streaming, PII masking, MetaDocument save (retrieval portion) |

---

## Subcomponents

The RetrievalEngine decomposes into 2 subcomponents.

---

### SUBCOMP-03A: RAGService (Hybrid Retrieval)

**Stories:** STORY-015
**Files:** `src/services/rag_service.py`, `src/schemas/rag.py`, `src/adapters/qdrant_adapter.py`, `src/adapters/neo4j_adapter.py`, `tests/unit/services/test_rag_service.py`, `tests/integration/services/test_rag_retrieval.py`

#### Details
`RAGService` extends `BaseService` and implements a 3-phase retrieval pipeline. Phase 1 runs Qdrant kNN semantic search for top-30 candidates. Phase 2 runs Neo4j Cypher traversal to find Memory nodes related to extracted concepts. Phase 3 merges, deduplicates, and re-ranks using the weighted formula. All queries are tenant-scoped. Adapters are injected via constructor for testability.

#### Criteria of Done
- [ ] `RAGService.retrieve(prompt, profile_id, tenant_id, limit)` returns `list[RetrievedChunk]`
- [ ] Phase 1: Qdrant kNN search with `tenant_id` + optional `profile_id` filter, returns top-30
- [ ] Phase 2: Neo4j Cypher query to find Memory nodes related to concepts in the prompt
- [ ] Phase 3: `final_score = semantic×0.6 + recency×0.3 + profile×0.1` applied to all candidates
- [ ] Deduplication by content hash (not chunk_id — same content may appear in both result sets)
- [ ] Returns top-N unique chunks with attribution (source_id, memory_id, page_number)
- [ ] Empty result returns `[]` — no error, no hallucination
- [ ] Performance: < 3 seconds for 10,000-chunk corpus

#### Checklist
- [ ] `RetrievedChunk` Pydantic schema in `src/schemas/rag.py` — written FIRST
- [ ] `RAGService` extends `BaseService` — adapters injected in constructor
- [ ] Qdrant adapter called with `tenant_id` filter in every search
- [ ] Neo4j adapter called with `tenant_id` in WHERE clause
- [ ] `extract_concepts()`: simple noun extraction from prompt for Neo4j traversal
- [ ] `recency_weight = 1.0 / (1.0 + age_days / 30)` — decays over months
- [ ] `profile_match = 1.0 if chunk.get("profile_id") else 0.5`
- [ ] Unit tests with mocked Qdrant + Neo4j adapters
- [ ] Integration tests with seeded data

#### Testing
```bash
# Unit tests:
uv run pytest tests/unit/services/test_rag_service.py -v

# Integration tests:
uv run pytest tests/integration/services/test_rag_retrieval.py -v

# Performance test:
uv run pytest tests/integration/services/test_rag_retrieval.py::test_retrieval_performance -v
# Expected: < 3 seconds for 10,000 chunks

# Quality:
make quality
```

---

### SUBCOMP-03B: Meta-Doc Retrieval Pipeline

**Stories:** STORY-016 (retrieval portion)
**Files:** `src/workers/metadoc_tasks.py`, `src/services/rag_service.py`, `src/adapters/presidio_adapter.py`, `src/adapters/anthropic_adapter.py`

#### Details
The `generate_meta_document` ARQ task uses `RAGService.retrieve()` to populate context, then runs PII masking via Presidio before sending to the LLM. The LLM streams tokens back via Redis pub/sub, which the SSE endpoint re-streams to the browser. This subcomponent covers the retrieval and PII-masking portions; the generation/SSE streaming is in COMP-04.

#### Criteria of Done
- [ ] `generate_meta_document` task calls `RAGService.retrieve()` with `limit=15` chunks
- [ ] Presidio PII masking runs on all retrieved chunks before LLM call (when `ENABLE_PII_MASKING=true`)
- [ ] PII masking is deterministic: same entity maps to same placeholder across all chunks
- [ ] `bleach.clean()` sanitizes LLM output before database write
- [ ] Context chunks formatted for system prompt with source attribution
- [ ] Generation timeout: 5 minutes via `asyncio.wait_for`
- [ ] On timeout: SSE emits `{type: "error", message: "Generation timed out"}` — no partial document saved

#### Checklist
- [ ] `ENABLE_PII_MASKING` setting gates Presidio call
- [ ] `PresidioAdapter` uses deterministic entity map (stable across calls for same input)
- [ ] `bleach.clean()` import at module level (safe utility library)
- [ ] System prompt includes source attribution for each chunk
- [ ] `asyncio.timeout(300)` on LLM streaming call
- [ ] Redis `publish` on `metadoc:stream:{job_id}` for each token
- [ ] `MetaDocument` saved to PostgreSQL after generation completes
- [ ] `CONTAINS` edges written to Neo4j for each contributing memory
- [ ] Credits deducted AFTER successful generation (not before)

#### Testing
```bash
# PII masking test:
# Set ENABLE_PII_MASKING=true, upload doc with "John Smith"
# Call generate endpoint
# Verify "John Smith" NOT in LLM input (check logs or mock)
# Expected: masked placeholder in LLM payload

# End-to-end:
# uv run python scripts/seed_dev_data.py
# curl -X POST http://localhost:8000/v1/metadoc/generate \
#   -H "Authorization: Bearer TOKEN" \
#   -d '{"prompt": "Summarize my skills", "profile_id": "UUID", "model": "sonnet"}'
# Expected: SSE tokens stream to browser

# Quality:
make quality
```
