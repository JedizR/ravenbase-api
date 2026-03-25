# STORY-025: PII Masking in Production + Presidio Config

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-016

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 5: secrets in env vars, RULE 6: lazy imports)
> 2. `docs/architecture/05-security-privacy.md` — PII masking requirements, Presidio entity types
> 3. `docs/architecture/04-background-jobs.md` — where masking integrates in the generation pipeline
> 4. `docs/development/02-coding-standards.md` — adapter pattern for PresidioAdapter

---

## User Story
As a user, I want my personal information to be masked before it's sent to external AI APIs so that my private data stays private.

## Acceptance Criteria
- [ ] AC-1: `PresidioAdapter` correctly masks: PERSON names, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, US_SSN, LOCATION
- [ ] AC-2: Format-preserving: "John" and "John" in different chunks both map to "Entity_001" consistently (not random)
- [ ] AC-3: Entity map persisted in Redis during a generation job (TTL: 1 hour) — cleared after job completes
- [ ] AC-4: Masked prompt sent to LLM; entity map used to restore proper nouns in final output (if needed)
- [ ] AC-5: PII masking enabled when `ENABLE_PII_MASKING=true` (production default: true)
- [ ] AC-6: Test: seeded chunk with "My name is John Smith, email john@example.com" → masked version sent to LLM mock → assert "John Smith" not in LLM payload
- [ ] AC-7: Masking adds < 500ms to generation pipeline

## Technical Notes

### Files to Create
- `src/adapters/presidio_adapter.py` — deterministic entity map, format-preserving pseudonyms

### Files to Modify
- `src/workers/metadoc_tasks.py` — gate masking on `settings.ENABLE_PII_MASKING`
- `src/workers/graph_tasks.py` — gate masking on `settings.ENABLE_PII_MASKING`

### PII Entities to Detect
`PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `US_SSN`, `LOCATION`

### Architecture Constraints
- `presidio_analyzer` + `presidio_anonymizer` imports MUST be inside function body (`# noqa: PLC0415`) — slow to import
- Entity map stored in Redis: key = `pii:map:{job_id}`, TTL = 3600 seconds
- Same entity across chunks MUST get same alias (consistency requirement)
- Clear entity map from Redis after job completes (in `finally` block)
- `ENABLE_PII_MASKING=false` in dev bypasses masking without code changes

### Consistency Requirement
```python
# Same name in different chunks MUST map to same alias
# 'John Smith' in chunk 1 → 'Entity_000'
# 'John Smith' in chunk 5 → 'Entity_000' (same alias, NOT Entity_001)
```

### PresidioAdapter Pattern
```python
# src/adapters/presidio_adapter.py
import json
from structlog import get_logger
from src.adapters.base import BaseAdapter

logger = get_logger()

class PresidioAdapter(BaseAdapter):
    """Deterministic PII masking with cross-chunk consistency via Redis entity map."""

    ENTITY_TYPES = [
        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
        "CREDIT_CARD", "US_SSN", "LOCATION",
    ]

    async def mask_text(
        self,
        text: str,
        job_id: str,
        redis,
    ) -> str:
        from presidio_analyzer import AnalyzerEngine  # noqa: PLC0415
        from presidio_anonymizer import AnonymizerEngine  # noqa: PLC0415
        from presidio_anonymizer.entities import OperatorConfig  # noqa: PLC0415

        analyzer = AnalyzerEngine()
        anonymizer = AnonymizerEngine()

        # Load existing entity map from Redis (for cross-chunk consistency)
        entity_map_key = f"pii:map:{job_id}"
        raw = await redis.get(entity_map_key)
        entity_map: dict[str, str] = json.loads(raw) if raw else {}

        results = analyzer.analyze(text=text, entities=self.ENTITY_TYPES, language="en")

        # Assign deterministic aliases
        operators = {}
        for result in results:
            original = text[result.start:result.end]
            if original not in entity_map:
                alias = f"Entity_{len(entity_map):03d}"
                entity_map[original] = alias
            operators[result.entity_type] = OperatorConfig(
                "replace", {"new_value": entity_map[original]}
            )

        # Persist updated entity map to Redis
        await redis.setex(entity_map_key, 3600, json.dumps(entity_map))

        masked_result = anonymizer.anonymize(
            text=text, analyzer_results=results, operators=operators
        )
        logger.info(
            "pii.masked",
            job_id=job_id,
            entities_found=len(results),
        )
        return masked_result.text
```

### Integration in Generation Pipeline
```python
# src/workers/metadoc_tasks.py
from src.core.config import settings

async def generate_meta_document(ctx, *, prompt, profile_id, tenant_id, job_id):
    # ... retrieve chunks from RAGService ...

    if settings.ENABLE_PII_MASKING:
        presidio = PresidioAdapter()
        masked_chunks = []
        for chunk in retrieved_chunks:
            masked_content = await presidio.mask_text(
                chunk.content, job_id=job_id, redis=ctx["redis"]
            )
            masked_chunks.append(masked_content)
    else:
        masked_chunks = [c.content for c in retrieved_chunks]

    # Build prompt from masked_chunks and call Anthropic
    # ...
    # In finally block: clear entity map
    try:
        pass  # generation
    finally:
        await ctx["redis"].delete(f"pii:map:{job_id}")
```

## Definition of Done (All EPIC-08)
- [ ] Production checklist in `development/05-operations.md` fully reviewed and checked
- [ ] All 25 stories in `stories/epics.md` marked DONE
- [ ] p95 query latency < 500ms measured in staging with k6
- [ ] GDPR deletion cascade tested end-to-end
- [ ] `make ci-local` passes from clean checkout

## Definition of Done (This Story)
- [ ] All 6 PII entity types masked in tests
- [ ] Consistent pseudonyms across multiple chunks (same entity → same alias)
- [ ] Entity map in Redis with correct TTL (1 hour)
- [ ] Entity map cleared from Redis after job completes
- [ ] Masking adds < 500ms overhead (measured)
- [ ] `ENABLE_PII_MASKING=false` bypasses masking in dev
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Unit tests:
uv run pytest tests/unit/adapters/test_presidio_adapter.py -v

# Critical test: assert PII not in LLM payload
uv run pytest tests/unit/adapters/test_presidio_adapter.py::test_pii_not_in_llm_payload -v
# This seeds "My name is John Smith, email john@example.com"
# Mocks Anthropic call and asserts "John Smith" not in payload

# Consistency test:
uv run pytest tests/unit/adapters/test_presidio_adapter.py::test_cross_chunk_consistency -v
# Same entity in chunk 1 and chunk 5 must get same alias

# Performance test:
uv run pytest tests/unit/adapters/test_presidio_adapter.py::test_masking_performance -v
# Expected: < 500ms for 10 chunks of 512 tokens each

# Quality:
make quality
```

**Passing result:** "John Smith" not in LLM payload. Same name in multiple chunks maps to same alias. Entity map in Redis with 1hr TTL. Performance < 500ms.

---

## Agent Implementation Brief

```
Implement STORY-025: PII Masking in Production + Presidio Config.

Read first:
1. CLAUDE.md (architecture rules — RULE 6: lazy imports for Presidio)
2. docs/architecture/05-security-privacy.md (PII masking requirements + entity types)
3. docs/architecture/04-background-jobs.md (where masking fits in metadoc pipeline)
4. docs/development/02-coding-standards.md (adapter pattern)
5. docs/stories/EPIC-08-polish/STORY-025.md (this file)

Key constraints:
- presidio_analyzer + presidio_anonymizer imports MUST be inside function (# noqa: PLC0415)
- Entity map in Redis key `pii:map:{job_id}`, TTL 3600 seconds
- Deterministic aliases: same entity text → same Entity_NNN alias (load map from Redis first)
- Entity map MUST be deleted in finally block after job completes
- Gate ALL masking on settings.ENABLE_PII_MASKING (false in dev, true in production)
- Test MUST assert "John Smith" is NOT in the Anthropic API call payload

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
git add -A && git commit -m "feat(ravenbase): STORY-025 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-025"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-025
git add docs/stories/epics.md && git commit -m "docs: mark STORY-025 complete"
```
