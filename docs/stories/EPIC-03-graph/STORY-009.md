# STORY-009: Entity Extraction (Gemini Flash via LLMRouter) + Neo4j Writer

**Epic:** EPIC-03 — Knowledge Graph Layer
**Priority:** P0
**Complexity:** Large
**Depends on:** STORY-006
**Type:** Backend
**Repo:** ravenbase-api

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 2 tenant isolation, RULE 6 lazy imports)
> 2. `docs/architecture/02-database-schema.md` — Neo4j node labels, relationship types, Key Cypher Queries
> 3. `docs/architecture/04-background-jobs.md` — ARQ task chaining pattern
> 4. `docs/architecture/01-tech-stack-decisions.md` — ADR-011 (LLMRouter + Gemini Flash for extraction)
> 5. `docs/development/02-coding-standards.md` — adapter pattern, exponential backoff

---

## User Story
As a user, I want the system to automatically identify the concepts, skills, and projects in my ingested content so that the knowledge graph builds itself from my data.

## Context
- Neo4j schema: `architecture/02-database-schema.md` — Node Labels, Relationship Types
- Background jobs: `architecture/04-background-jobs.md` — `extract_entities`, `write_graph_nodes`
- LLM pattern: `development/02-coding-standards.md` — adapter pattern for LLM calls

## Acceptance Criteria
- [ ] AC-1: `extract_entities` ARQ task calls `LLMRouter().complete("entity_extraction", messages, response_format={"type":"json_object"})` — routes to Gemini 2.5 Flash with Claude Haiku as automatic fallback
- [ ] AC-2: Extraction prompt produces: `{entities: [{name, type, confidence}], memories: [{content, confidence}], relationships: [{from, to, type}]}`
- [ ] AC-3: LLMRouter called with `response_format={"type": "json_object"}` — enforces structured output regardless of which provider handles the call
- [ ] AC-4: `write_graph_nodes` task writes Concept + Memory nodes to Neo4j with correct properties
- [ ] AC-5: All Neo4j nodes include `tenant_id` property (enforced in `neo4j_adapter.write_nodes()`)
- [ ] AC-6: Deduplication: if a Concept with same `name` + `tenant_id` exists, MERGE (not create duplicate)
- [ ] AC-7: `EXTRACTED_FROM` and `RELATES_TO` relationships written with correct properties
- [ ] AC-8: Source status updated to `completed` after graph nodes written
- [ ] AC-9: Cost tracking: LLM tokens consumed (input + output) logged to structlog via `LLMRouter` metadata callback, regardless of which provider handled the call
- [ ] AC-10: 50-page document: graph extraction completes within 3 minutes

## Technical Notes

### Files to Create
- `src/workers/graph_tasks.py` — `extract_entities`, `write_graph_nodes` tasks
- `src/adapters/llm_router.py` — use this for entity extraction (not anthropic_adapter.py directly)
- `src/services/graph_service.py` — orchestrates entity extraction and Neo4j writes
- `tests/unit/services/test_graph_service.py`
- `tests/integration/workers/test_graph_tasks.py`

### Architecture Constraints
- Anthropic import MUST be inside function (`# noqa: PLC0415`)
- Implement exponential backoff for Anthropic rate limit errors (429)
- If extraction fails for a chunk, log + skip (don't fail the entire source)
- All Neo4j MERGE statements MUST include `tenant_id` in the MERGE key

### Extraction Prompt
```python
ENTITY_EXTRACTION_PROMPT = """
Extract entities and facts from the following text chunk.

Return ONLY valid JSON in this exact schema:
{
  "entities": [
    {"name": "string", "type": "skill|tool|project|person|org|decision", "confidence": 0.0-1.0}
  ],
  "memories": [
    {"content": "A single factual statement about the user", "confidence": 0.0-1.0}
  ],
  "relationships": [
    {"from_entity": "name", "to_entity": "name", "type": "USES|WORKED_ON|LED|KNOWS|DECIDED"}
  ]
}

Rules:
- Only extract facts explicitly stated in the text
- Memories must be first-person statements ("User worked on...", "User prefers...")
- Confidence < 0.6: skip the entity
- Maximum 10 entities, 5 memories, 5 relationships per chunk

Text:
{chunk_content}
"""
```

### Neo4j MERGE Pattern (deduplication)
```cypher
// Concept node — MERGE prevents duplicates
MERGE (c:Concept {name: $name, tenant_id: $tenant_id})
ON CREATE SET c.concept_id = $concept_id, c.created_at = datetime()
ON MATCH SET c.updated_at = datetime()

// Memory node
CREATE (m:Memory {
  memory_id: $memory_id,
  content: $content,
  tenant_id: $tenant_id,
  source_id: $source_id,
  created_at: datetime()
})

// Relationships
MATCH (m:Memory {memory_id: $memory_id, tenant_id: $tenant_id})
MATCH (c:Concept {name: $entity_name, tenant_id: $tenant_id})
MERGE (m)-[:EXTRACTED_FROM]->(c)
```

### LLMRouter Pattern (entity extraction)
```python
# src/workers/tasks/graph_extraction.py — call LLMRouter, not Anthropic directly
from src.adapters.llm_router import LLMRouter

router = LLMRouter()

async def extract_entities_from_chunk(prompt: str, tenant_id: str) -> dict:
    """
    Routes to Gemini 2.5 Flash (primary) with Claude Haiku fallback.
    litellm handles retries and provider switching automatically.
    """
    result = await router.complete(
        task="entity_extraction",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=1024,
    )
    return json.loads(result)
```

## Definition of Done
- [ ] Entity extraction runs automatically after ingestion completes (task chaining)
- [ ] Neo4j has Concept + Memory nodes with correct properties and tenant_id
- [ ] MERGE prevents duplicate Concept nodes
- [ ] Token usage logged to structlog for credit accounting
- [ ] Integration test confirms tenant isolation (user A's nodes not visible to user B)
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Unit tests:
uv run pytest tests/unit/services/test_graph_service.py -v

# Integration tests (requires Neo4j running):
uv run pytest tests/integration/workers/test_graph_tasks.py -v

# Verify Neo4j nodes after ingestion:
# Open Neo4j Browser at http://localhost:7474
# Run: MATCH (n) WHERE n.tenant_id = "your-tenant-id" RETURN n LIMIT 25

# Quality:
make quality
```

**Passing result:** Entity extraction completes for a 50-page document within 3 minutes. Neo4j contains Concept and Memory nodes with correct tenant_id. No duplicate Concept nodes.

---

## Agent Implementation Brief

```
Implement STORY-009: Entity Extraction (Gemini Flash via LLMRouter) + Neo4j Writer.

Read first:
1. CLAUDE.md (architecture rules — RULE 2: tenant isolation, RULE 6: lazy imports)
2. docs/architecture/02-database-schema.md (Neo4j labels, relationship types, Key Cypher Queries)
3. docs/architecture/04-background-jobs.md (ARQ task chaining pattern)
4. docs/architecture/01-tech-stack-decisions.md (ADR-011: LLMRouter + Gemini Flash)
5. docs/stories/EPIC-03-graph/STORY-009.md (this file)

Key constraints:
- `from anthropic import ...` MUST be inside function body (# noqa: PLC0415)
- Use MERGE (not CREATE) for Concept nodes — prevents duplicates across chunks
- MERGE key MUST include tenant_id: MERGE (c:Concept {name: $name, tenant_id: $tenant_id})
- Exponential backoff for 429 errors (max 3 attempts)
- Failed chunk extraction: log to structlog + skip chunk, do NOT fail the entire task
- Token count logged to structlog after each Anthropic call

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
git add -A && git commit -m "feat(ravenbase): STORY-009 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-009"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-009
git add docs/stories/epics.md && git commit -m "docs: mark STORY-009 complete"
```
