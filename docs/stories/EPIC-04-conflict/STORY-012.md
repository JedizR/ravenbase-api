# STORY-012: Conflict Detection Worker

**Epic:** EPIC-04 — Conflict Detection & Memory Inbox
**Priority:** P0
**Complexity:** Large
**Depends on:** STORY-009

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-05-AC-1: Qdrant similarity scan identifies candidate contradictions above threshold per tenant
- FR-05-AC-2: LLM classifies each candidate as CONTRADICTION, DUPLICATE, or NOT_CONFLICT
- FR-05-AC-3: Conflict record created in PostgreSQL with status PENDING
- FR-05-AC-4: Confidence score stored on each Conflict record

## Component
COMP-02: GraphEngine

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 2 tenant isolation)
> 2. `docs/prd/03-feature-specs/F3-memory-inbox.md` — full 5-step conflict detection algorithm
> 3. `docs/architecture/02-database-schema.md` — Conflict table, ConflictStatus, Neo4j CONTRADICTS edge
> 4. `docs/architecture/04-background-jobs.md` — ARQ task chaining pattern
> 5. `docs/architecture/01-tech-stack-decisions.md` — ADR-011 (LLMRouter + Gemini Flash for classification)

---

## User Story
As a user, I want the system to automatically detect when new information contradicts existing memories so that I know when to update my knowledge graph.

## Context
- Conflict algorithm: `prd/03-feature-specs/F3-memory-inbox.md` — full 5-step algorithm
- Data models: `architecture/02-database-schema.md` — Conflict table, Neo4j CONTRADICTS edge
- Background jobs: `architecture/04-background-jobs.md`

## Acceptance Criteria
- [ ] AC-1: `scan_for_conflicts` task runs automatically after `write_graph_nodes` completes
- [ ] AC-2: Qdrant cosine similarity scan finds embeddings > 0.87 threshold vs new memory embeddings
- [ ] AC-3: Candidate pairs sent via `LLMRouter().complete("conflict_classification", messages, response_format={"type":"json_object"})` — Gemini 2.5 Flash primary, Claude Haiku automatic fallback
- [ ] AC-4: Classification prompt uses JSON mode, returns `{classification: "CONTRADICTION|UPDATE|COMPLEMENT|DUPLICATE", confidence: 0.0-1.0, reasoning: string}`
- [ ] AC-5: CONTRADICTION or UPDATE: `Conflict` record created in PostgreSQL with both memory content snapshots
- [ ] AC-6: CONTRADICTS Neo4j edge written between the two Memory nodes
- [ ] AC-7: Auto-resolution: if challenger source authority weight > incumbent by 3+ points, auto-resolve with `status=auto_resolved`
- [ ] AC-8: Redis pub/sub notification: `conflict:new:{tenant_id}` channel updated (for SSE to inbox subscribers)
- [ ] AC-9: Maximum 5 conflicts created per ingestion batch (prevent notification fatigue from large uploads)
- [ ] AC-10: COMPLEMENT: write TEMPORAL_LINK edge in Neo4j (no conflict created)

## Technical Notes

### Files to Create
- `src/workers/conflict_tasks.py` — `scan_for_conflicts`, `classify_conflict` tasks
- `src/services/conflict_service.py` — detection + auto-resolution logic
- `tests/integration/workers/test_conflict_detection.py`

### Critical Test: Tenant Isolation
```python
def test_conflict_detection_tenant_isolation():
    """User A's memory must NEVER match against User B's memories in Qdrant scan."""
    # Seed identical text for 2 different tenant_ids
    # Run scan for user A — assert only user A's memories returned as candidates
```

### Qdrant Similarity Search Pattern (tenant-scoped)
```python
# ALWAYS include tenant_id filter — never scan across tenants
results = qdrant_client.search(
    collection_name="memories",
    query_vector=new_memory_embedding,
    query_filter=Filter(
        must=[
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
        ]
    ),
    score_threshold=0.87,
    limit=10,
)
```

### Conflict Classification Prompt
```python
CLASSIFY_PROMPT = """
Classify the relationship between these two statements about the same person.

Statement A (older): {incumbent}
Statement B (newer): {challenger}

Return JSON only:
{
  "classification": "CONTRADICTION|UPDATE|COMPLEMENT|DUPLICATE",
  "confidence": 0.0-1.0,
  "reasoning": "one sentence"
}

CONTRADICTION: directly opposing facts
UPDATE: B supersedes A (skill changed, job changed)
COMPLEMENT: adds information without contradiction
DUPLICATE: same meaning, different wording
"""
```

### Auto-Resolution Logic
```python
async def maybe_auto_resolve(
    conflict: Conflict,
    incumbent_source: Source,
    challenger_source: Source,
) -> bool:
    incumbent_weight = incumbent_source.authority_weight or 0
    challenger_weight = challenger_source.authority_weight or 0
    if challenger_weight - incumbent_weight >= 3:
        conflict.status = ConflictStatus.AUTO_RESOLVED
        conflict.resolution_note = f"Auto-resolved: challenger authority +{challenger_weight - incumbent_weight}"
        return True
    return False
```

### Architecture Constraints
- Qdrant search MUST include `tenant_id` filter — no cross-tenant data leakage
- Maximum 5 conflicts per batch (slice candidates list before creating Conflict records)
- CONTRADICTS Neo4j edge must use tenant_id in WHERE clause when matching Memory nodes
- Redis notification MUST fire after Conflict record is committed to PostgreSQL
- Use `LLMRouter().complete("conflict_classification", ...)` — never call Anthropic directly for classification

## Definition of Done
- [ ] `scan_for_conflicts` runs after each successful ingestion
- [ ] Qdrant cosine similarity correctly finds candidate pairs above 0.87 threshold
- [ ] Conflict records created in PostgreSQL for CONTRADICTION + UPDATE classifications
- [ ] CONTRADICTS Neo4j edges written
- [ ] Auto-resolution triggers when authority weight delta >= 3
- [ ] Tenant isolation test passes (user A cannot see user B's memories)
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Integration tests:
uv run pytest tests/integration/workers/test_conflict_detection.py -v

# Tenant isolation test (critical):
uv run pytest tests/integration/workers/test_conflict_detection.py::test_conflict_detection_tenant_isolation -v

# Manual test — upload two conflicting documents for same user:
# 1. Upload doc1: "I am a senior Python developer"
# 2. Upload doc2: "I am a junior Python developer"
# 3. After both ingested, check PostgreSQL conflicts table:
# Expected: 1 conflict record with classification=CONTRADICTION

# Quality:
make quality
```

**Passing result:** Conflict detected and stored in PostgreSQL. CONTRADICTS edge in Neo4j. Redis notification sent. Tenant isolation test passes.

---

## Agent Implementation Brief

```
Implement STORY-012: Conflict Detection Worker.

Read first:
1. CLAUDE.md (architecture rules — RULE 2: tenant isolation is critical here)
2. docs/prd/03-feature-specs/F3-memory-inbox.md (5-step conflict detection algorithm)
3. docs/architecture/02-database-schema.md (Conflict model, ConflictStatus, Neo4j CONTRADICTS)
4. docs/architecture/04-background-jobs.md (ARQ task chaining)
5. docs/stories/EPIC-04-conflict/STORY-012.md (this file)

Key constraints:
- Qdrant search MUST include tenant_id filter (FieldCondition on key="tenant_id")
- Score threshold: 0.87 cosine similarity
- Max 5 conflicts per ingestion batch — slice results before creating records
- Auto-resolve if challenger authority_weight - incumbent_weight >= 3
- Redis pub/sub notification on channel `conflict:new:{tenant_id}` after DB commit
- Tenant isolation test is MANDATORY before marking done

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
git add -A && git commit -m "feat(ravenbase): STORY-012 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-012"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-012
git add docs/stories/epics.md && git commit -m "docs: mark STORY-012 complete"
```
