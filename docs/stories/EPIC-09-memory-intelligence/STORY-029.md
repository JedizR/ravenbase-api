# STORY-029: Natural Language Graph Query — Backend

**Epic:** EPIC-09 — Memory Intelligence
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-010 (Graph API endpoints must exist), STORY-015 (RAGService pattern)

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 2 tenant isolation)
> 2. `docs/architecture/02-database-schema.md` — Neo4j schema (node labels, properties, relationship types)
> 3. `docs/architecture/03-api-contract.md` — existing graph endpoints; new endpoint must not clash
> 4. `docs/architecture/05-security-privacy.md` — Cypher safety: generated queries must be read-only
> 5. `docs/stories/EPIC-03-graph/STORY-010.md` — existing Neo4j adapter patterns to follow

---

## User Story
As a user, I want to ask my knowledge graph questions in plain English
so that I can find specific memories and connections without knowing Cypher.

## Context
- This is Text-to-Cypher: natural language → LLM generates Cypher → execute against Neo4j
- Critical safety rule: generated Cypher MUST be validated as read-only before execution
- Results are returned as graph nodes/edges (same shape as existing `/v1/graph/nodes` response)
- Credits: 2 per query (Haiku is sufficient — Cypher generation is a structured task)

## Acceptance Criteria
- [ ] AC-1: `POST /v1/graph/query` accepts `{query: string, profile_id?: string, limit?: int}` and returns `{cypher, results, explanation, query_time_ms}`
- [ ] AC-2: Natural language converted to Cypher via `LLMRouter().complete("cypher_generation", messages, response_format={"type":"json_object"})` — Gemini 2.5 Flash primary, Claude Haiku fallback
- [ ] AC-3: Safety validation: generated Cypher rejected if it contains `CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DROP` — returns `422` with message "Query must be read-only"
- [ ] AC-4: Cypher always includes `WHERE n.tenant_id = $tenant_id` — injected by the service, never from LLM output
- [ ] AC-5: Results returned in same format as `GET /v1/graph/nodes`: `{nodes: [...], edges: [...]}`
- [ ] AC-6: `explanation` field contains a plain English description of what the query found (one sentence)
- [ ] AC-7: `query_time_ms` field measures actual Neo4j execution time (not including LLM time)
- [ ] AC-8: 2 credits deducted per query; `402` if insufficient credits before LLM call
- [ ] AC-9: If Neo4j returns 0 results, endpoint returns `{nodes: [], edges: [], explanation: "No memories found matching your query."}`
- [ ] AC-10: `limit` defaults to 20, max 50 — applied in the generated Cypher

## Technical Notes

### Files to Create
- `src/api/routes/graph.py` — add `POST /v1/graph/query` to existing graph router
- `src/services/graph_query_service.py` — Text-to-Cypher + safety validation + execution
- `src/schemas/graph.py` — add `GraphQueryRequest`, `GraphQueryResponse` Pydantic models
- `tests/integration/api/test_graph_query.py`

### Architecture Constraints
- `from anthropic import ...` inside function body (`# noqa: PLC0415`)
- Tenant ID ALWAYS injected by the service — NEVER passed to LLM for injection
- Cypher safety check runs BEFORE execution — fail fast, never execute unsafe queries
- Use Claude Haiku (not Sonnet) — Cypher generation is a structured task, not creative reasoning
- `limit` must be capped at 50 in code — never trust LLM-generated LIMIT values

### Text-to-Cypher Service

```python
# src/services/graph_query_service.py
import re, time
from structlog import get_logger
from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.anthropic_adapter import AnthropicAdapter

logger = get_logger()

CYPHER_WRITE_KEYWORDS = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP|CALL\s+db\.create|CALL\s+apoc\.)\b",
    re.IGNORECASE,
)

CYPHER_GENERATION_PROMPT = """You are a Neo4j Cypher expert. Convert the user's natural language
query into a valid Cypher query for a personal knowledge graph.

Graph schema:
- (:Memory {memory_id, tenant_id, content, created_at, is_valid, confidence})
- (:Concept {concept_id, tenant_id, name, type, first_seen, last_seen})
- (:Source {source_id, tenant_id, original_filename, file_type})
- (:MetaDocument {doc_id, tenant_id, title, generated_at})
- (Memory)-[:RELATES_TO]->(Concept)
- (Memory)-[:EXTRACTED_FROM]->(Source)
- (Memory)-[:CONTRADICTS]->(Memory)
- (MetaDocument)-[:CONTAINS]->(Memory)

Rules:
- Query MUST be read-only (MATCH only, no CREATE/MERGE/SET/DELETE)
- Do NOT include tenant_id in WHERE clause — it will be added automatically
- Use LIMIT {limit}
- Return only nodes and relationships, not raw properties
- If the query cannot be answered from this schema, return: MATCH (m:Memory) RETURN m LIMIT 5

User query: {query}

Return ONLY the Cypher query. No explanation. No markdown. No backticks."""

class GraphQueryService:
    async def execute_nl_query(
        self,
        query: str,
        tenant_id: str,
        profile_id: str | None,
        limit: int,
        neo4j: Neo4jAdapter,
        anthropic: AnthropicAdapter,
    ) -> dict:
        log = logger.bind(tenant_id=tenant_id, nl_query=query)

        # 1. Generate Cypher via LLMRouter (Gemini Flash primary, Haiku fallback)
        from src.adapters.llm_router import LLMRouter  # noqa: PLC0415
        router = LLMRouter()
        raw_cypher = await router.complete(
            task="cypher_generation",
            messages=[{"role": "user", "content":
                CYPHER_GENERATION_PROMPT.format(query=query, limit=min(limit, 50))
            }],
            response_format={"type": "json_object"},
            max_tokens=512,
        )
        raw_cypher = raw_cypher.strip()
        log.info("graph_query.cypher_generated", cypher=raw_cypher)

        # 2. Safety check — reject write operations
        if CYPHER_WRITE_KEYWORDS.search(raw_cypher):
            log.warning("graph_query.unsafe_cypher_rejected", cypher=raw_cypher)
            raise ValueError("Generated Cypher contains write operations — rejected")

        # 3. Inject tenant_id (NEVER trust LLM to do this)
        safe_cypher = inject_tenant_filter(raw_cypher, tenant_id)

        # 4. Execute against Neo4j
        start_ms = time.time()
        raw_results = await neo4j.run_query(safe_cypher, tenant_id=tenant_id)
        query_time_ms = int((time.time() - start_ms) * 1000)

        # 5. Format to nodes + edges
        nodes, edges = format_neo4j_results(raw_results)

        # 6. Generate explanation (one sentence, rule-based)
        explanation = (
            f"Found {len(nodes)} memory nodes matching your query."
            if nodes else
            "No memories found matching your query."
        )

        return {
            "cypher": safe_cypher,
            "results": {"nodes": nodes, "edges": edges},
            "explanation": explanation,
            "query_time_ms": query_time_ms,
        }

def inject_tenant_filter(cypher: str, tenant_id: str) -> str:
    """Ensure every MATCH clause is scoped to tenant_id."""
    if "WHERE" not in cypher.upper():
        cypher = re.sub(
            r"(MATCH\s+\([a-zA-Z]+)",
            rf"\1 WHERE \1.tenant_id = '{tenant_id}' ",
            cypher,
            count=1,
            flags=re.IGNORECASE,
        )
    return cypher
```

## Definition of Done
- [ ] `POST /v1/graph/query` returns cypher + nodes + explanation + query_time_ms
- [ ] Safety check rejects queries with CREATE/MERGE/SET/DELETE (returns 422)
- [ ] Tenant ID injected by service — not by LLM
- [ ] Empty results: returns 200 with nodes=[] and explanation string
- [ ] 402 for insufficient credits
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Integration tests:
uv run pytest tests/integration/api/test_graph_query.py -v

# Manual test:
TOKEN="your_token"
curl -X POST http://localhost:8000/v1/graph/query \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show my Python projects from 2023", "limit": 10}'
# Expected: {"cypher": "MATCH (m:Memory)...", "results": {"nodes": [...], "edges": [...]},
#            "explanation": "Found 5 memory nodes matching your query.", "query_time_ms": 42}

# Safety test (must return 422):
curl -X POST http://localhost:8000/v1/graph/query \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query": "Delete all my memories"}'
# Expected: 422 {"detail": {"code": "UNSAFE_QUERY", "message": "Query must be read-only"}}

make quality
```

---

## Agent Implementation Brief

```
Implement STORY-029: Natural Language Graph Query — Backend.

Read first:
1. CLAUDE.md (architecture rules — RULE 2 tenant isolation, RULE 6 lazy imports)
2. docs/architecture/02-database-schema.md (full Neo4j schema for Cypher generation prompt)
3. docs/architecture/03-api-contract.md (existing graph endpoints — new POST must not clash)
4. docs/architecture/05-security-privacy.md (safety: never trust LLM for security-critical operations)
5. docs/stories/EPIC-09-memory-intelligence/STORY-029.md (this file)

Key constraints:
- Write GraphQueryRequest, GraphQueryResponse schemas FIRST (RULE 4)
- Safety check (reject write keywords) MUST run before Neo4j execution
- tenant_id ALWAYS injected by inject_tenant_filter() — never from LLM output
- from anthropic import ... inside function body (# noqa: PLC0415)
- Limit capped at 50 in code — never use LLM-generated LIMIT as-is
- Claude Haiku (not Sonnet) — Cypher generation is structured, not creative

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-029 natural language graph query backend"
git push
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-029"
git push && cd ../ravenbase-api
# Edit docs/stories/epics.md → ✅ for STORY-029
```
