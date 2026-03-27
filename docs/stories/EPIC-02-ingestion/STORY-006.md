# STORY-006: Docling Parse + Chunk + Embed Worker

**Epic:** EPIC-02 — Ingestion Pipeline
**Priority:** P0
**Complexity:** Large
**Depends on:** STORY-005
**Type:** Backend
**Repo:** ravenbase-api

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 3: ARQ, RULE 6: lazy imports)
> 2. `docs/architecture/04-background-jobs.md` — ARQ task patterns, `publish_progress()` pattern
> 3. `docs/architecture/01-tech-stack-decisions.md` — ADR-002 (Docling), ADR-003 (Qdrant), ADR-004 (OpenAI embeddings)
> 4. `docs/architecture/02-database-schema.md` — Source model, SourceStatus constants
> 5. `docs/development/02-coding-standards.md` — adapter pattern, structlog usage

---

## User Story
As a user, I want my uploaded PDF to be automatically parsed, chunked, and indexed so I can search its content via the Omnibar.

## Context
- Worker setup: `architecture/04-background-jobs.md` — task patterns
- Docling notes: ADR-002 in `architecture/01-tech-stack-decisions.md`
- Adapter pattern: `development/02-coding-standards.md`

## Acceptance Criteria
- [ ] AC-1: `parse_document` ARQ task processes a PDF and produces chunks
- [ ] AC-2: Docling uses `pypdfium2` backend with `generate_page_images=False`, `generate_picture_images=False`
- [ ] AC-3: Chunking: 512-token chunks with 50-token overlap, preserving paragraph boundaries
- [ ] AC-4: Embeddings generated via OpenAI `text-embedding-3-small` in batches of 100 (not one-by-one)
- [ ] AC-5: Chunks upserted to Qdrant with `tenant_id`, `source_id`, `chunk_id`, `profile_id`, `page_number`, `created_at`
- [ ] AC-6: Source status updated: `pending → processing → indexing → completed`
- [ ] AC-7: Job progress published to Redis pub/sub channel `job:progress:{source_id}` at each stage
- [ ] AC-8: Corrupted/unreadable PDF: task marks source as `failed`, logs error, does NOT retry (to avoid billing waste)
- [ ] AC-9: A 10-page PDF completes ingestion within 60 seconds (without GPU)
- [ ] AC-10: After completion, `graph_extraction` job enqueued automatically
- [ ] AC-11: Before calling Docling, the first extracted text preview (up to 4,000 characters) is passed to `ModerationAdapter().check_content()`. If hard-reject categories are flagged: source is marked `failed` with message "Content flagged by safety system" AND `User.is_active` is set to `False`. Soft-reject: source marked `failed` only. If moderation API is unavailable: log warning and continue processing (fail open).

## Technical Notes

### Files to Create
- `src/workers/ingestion_tasks.py` — `parse_document`, `generate_embeddings` tasks
- `src/adapters/docling_adapter.py` — wraps Docling, lazy import
- `src/adapters/openai_adapter.py` — wraps OpenAI embeddings, handles batching
- `src/services/ingestion_service.py` — orchestration logic
- `tests/integration/workers/test_ingestion_tasks.py`

### Architecture Constraints
- Docling import MUST be inside function body (`# noqa: PLC0415`) — it's very slow to import
- OpenAI calls MUST be batched — never call embeddings one-by-one
- Blocking Docling code MUST run in `run_in_executor` — never block the event loop

### Docling Adapter Pattern
```python
# src/adapters/docling_adapter.py
from structlog import get_logger
from src.adapters.base import BaseAdapter

logger = get_logger()

class DoclingAdapter(BaseAdapter):
    def parse(self, content: bytes, filename: str) -> list[str]:
        from docling.document_converter import DocumentConverter  # noqa: PLC0415
        from docling.datamodel.pipeline_options import PdfPipelineOptions  # noqa: PLC0415

        options = PdfPipelineOptions(
            generate_page_images=False,
            generate_picture_images=False,
        )
        converter = DocumentConverter()
        result = converter.convert_from_bytes(content, filename=filename)
        return result.document.export_to_markdown()
```

### Embedding Batch Pattern
```python
# OpenAI embeddings — always batch, never one-by-one
async def embed_chunks(chunks: list[str], client: AsyncOpenAI) -> list[list[float]]:
    BATCH_SIZE = 100
    embeddings = []
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        embeddings.extend([r.embedding for r in response.data])
    return embeddings
```

### Progress Publishing Pattern
```python
import json
await redis.publish(
    f"job:progress:{source_id}",
    json.dumps({"progress_pct": 25, "message": "Parsing document...", "status": "processing"}),
)
```

## Definition of Done
- [ ] 10-page PDF ingested within 60 seconds
- [ ] Source status transitions correctly: pending → processing → indexing → completed
- [ ] Chunks appear in Qdrant with correct tenant_id filter
- [ ] `graph_extraction` job enqueued in ARQ after completion
- [ ] Corrupted PDF sets status=failed (no retry)
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Integration test:
uv run pytest tests/integration/workers/test_ingestion_tasks.py -v

# Verify Qdrant chunks after ingestion:
# (Connect to Qdrant dashboard at http://localhost:6333/dashboard)
# Expected: chunks for source_id visible with tenant_id payload

# Check ARQ job queue after upload:
redis-cli LRANGE arq:queue:default 0 -1
# Expected: graph_extraction job enqueued

# Quality:
make quality
```

**Passing result:** PDF parsed, chunked, embedded, and stored in Qdrant. Source status = completed. `graph_extraction` job enqueued automatically.

### Content Moderation (run BEFORE Docling)

```python
# parse_document task — first action before Docling:
try:
    preview = await extract_text_preview(file_path, max_chars=4000)
    await ModerationAdapter().check_content(preview, source_id, tenant_id)
except ModerationError as e:
    await update_job_status(source_id, "failed", "Content flagged by safety system")
    if e.hard:
        await flag_user_account(tenant_id)  # User.is_active = False
    return  # Stop — do not process flagged content
# ... continue with Docling
```

---

## Agent Implementation Brief

```
Implement STORY-006: Docling Parse + Chunk + Embed Worker.

Read first:
1. CLAUDE.md (architecture rules — RULE 6: lazy imports for Docling/OpenAI)
2. docs/architecture/04-background-jobs.md (ARQ task patterns, WorkerSettings)
3. docs/architecture/01-tech-stack-decisions.md (ADR-002 Docling, ADR-003 Qdrant)
4. docs/architecture/02-database-schema.md (Source model, SourceStatus)
5. docs/development/02-coding-standards.md (adapter pattern)
6. docs/stories/EPIC-02-ingestion/STORY-006.md (this file)

Key constraints:
- `from docling...` MUST be inside function body (# noqa: PLC0415) — never at module level
- OpenAI embeddings MUST be batched in groups of 100 (never one call per chunk)
- Blocking Docling parse MUST run in loop.run_in_executor(None, ...) — not bare await
- Source status updates: pending → processing → indexing → completed
- Progress events on Redis pub/sub channel `job:progress:{source_id}`
- On failure: set status=failed, log with structlog, do NOT re-raise (no ARQ retry)

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
git add -A && git commit -m "feat(ravenbase): STORY-006 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-006"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-006
git add docs/stories/epics.md && git commit -m "docs: mark STORY-006 complete"
```
