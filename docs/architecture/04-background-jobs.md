# Architecture — 04. Background Jobs (ARQ)

> **Cross-references:** `architecture/00-system-overview.md` | `development/02-coding-standards.md`
>
> **Rule:** Any operation taking >2 seconds MUST go through ARQ. No exceptions.

---

## ARQ Overview

ARQ is a Python async job queue backed by Redis. It integrates natively with FastAPI's asyncio event loop.

```python
# src/workers/main.py — worker entrypoint
import asyncio
from arq import create_pool
from arq.connections import RedisSettings

from src.workers.ingestion_tasks import parse_document, generate_embeddings
from src.workers.graph_tasks import extract_entities, write_graph_nodes
from src.workers.conflict_tasks import scan_for_conflicts, classify_conflict
from src.workers.deletion_tasks import cascade_delete_source
from src.workers.metadoc_tasks import generate_meta_document
from src.core.config import settings

class WorkerSettings:
    functions = [
        parse_document,
        generate_embeddings,
        extract_entities,
        write_graph_nodes,
        scan_for_conflicts,
        classify_conflict,
        cascade_delete_source,
        generate_meta_document,
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10                          # Concurrent jobs per worker
    job_timeout = 600                      # 10 min max per job
    keep_result = 3600                     # Keep result in Redis for 1 hour
    retry_jobs = True
    max_tries = 3

# Run with: arq src.workers.main.WorkerSettings
```

---

## FastAPI Lifespan — ARQ Pool Initialization (MANDATORY Pattern)

The ARQ Redis pool MUST be created once at application startup and stored in `app.state`.
Creating a pool per-request is a critical performance and reliability bug.

```python
# src/api/main.py — CORRECT lifespan pattern
from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from src.core.config import settings
from src.core.logging import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup
    setup_logging(is_production=settings.is_production)
    app.state.arq_pool = await create_pool(
        RedisSettings.from_dsn(settings.REDIS_URL)
    )
    yield
    # ── Shutdown
    await app.state.arq_pool.aclose()

app = FastAPI(title="Ravenbase API", version="1.0.0", lifespan=lifespan)
```

In every route handler that enqueues a job, access the pool via `request.app.state.arq_pool`:

```python
# src/api/routes/ingest.py — CORRECT pool access
from fastapi import Request

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile,
    request: Request,
    user: dict = Depends(require_user),
) -> UploadResponse:
    content = await file.read()
    # ✅ Correct: use the shared pool from app.state
    job = await request.app.state.arq_pool.enqueue_job(
        "parse_document",
        content=content,
        filename=file.filename,
        tenant_id=user["user_id"],
        source_id=str(source_id),
    )
    return UploadResponse(job_id=job.job_id, source_id=source_id, status="queued")
```

```python
# ❌ WRONG — never do this (creates new pool per request):
pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
job = await pool.enqueue_job(...)
```

---

## Enqueuing Jobs from API Routes

```python
# src/api/routes/ingest.py — how routes enqueue jobs
from arq import create_pool
from src.core.config import settings

async def enqueue_ingestion(
    content: bytes,
    filename: str,
    tenant_id: str,
    source_id: str,
    profile_id: str | None,
) -> str:
    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    job = await pool.enqueue_job(
        "parse_document",
        content=content,
        filename=filename,
        tenant_id=tenant_id,
        source_id=source_id,
        profile_id=profile_id,
        _job_id=f"ingest:{source_id}",    # Deterministic ID for deduplication
    )
    return job.job_id
```

---

## Queue Definitions

| Queue / Task | Priority | Timeout | Retry | Description |
|---|---|---|---|---|
| `parse_document` | High | 300s | 3x | Docling parse + chunking |
| `generate_embeddings` | High | 120s | 3x | OpenAI batch embedding |
| `extract_entities` | Medium | 120s | 3x | Claude Haiku entity extraction |
| `write_graph_nodes` | Medium | 60s | 3x | Neo4j node/edge writes |
| `scan_for_conflicts` | Medium | 180s | 2x | Qdrant similarity scan |
| `classify_conflict` | Medium | 60s | 2x | Claude Haiku classification |
| `cascade_delete_source` | Critical | 120s | 1x | Cascade deletion |
| `generate_meta_document` | Medium | 300s | 1x | Hybrid retrieve + LLM stream |

---

## Task Implementations

### `parse_document`

```python
# src/workers/ingestion_tasks.py
import structlog
from arq import Ctx
from src.services.ingestion_service import IngestionService
from src.adapters.docling_adapter import DoclingAdapter

logger = structlog.get_logger()

async def parse_document(
    ctx: Ctx,
    *,
    content: bytes,
    filename: str,
    tenant_id: str,
    source_id: str,
    profile_id: str | None,
) -> dict:
    log = logger.bind(tenant_id=tenant_id, source_id=source_id, job="parse_document")
    log.info("parse_document.started", filename=filename, size_bytes=len(content))

    try:
        await update_job_status(source_id, "active", 5, "Parsing document...")
        service = IngestionService()

        chunks = await service.parse_and_chunk(content, filename)
        log.info("parse_document.chunks_ready", chunk_count=len(chunks))

        await update_job_status(source_id, "active", 30, "Generating embeddings...")
        embeddings = await service.embed_chunks(chunks, tenant_id, source_id, profile_id)

        await update_job_status(source_id, "active", 70, "Indexing to vector store...")
        await service.upsert_to_qdrant(embeddings, tenant_id)

        await update_job_status(source_id, "indexing", 80, "Building knowledge graph...")
        # Enqueue next step
        pool = ctx["redis"]
        await pool.enqueue_job(
            "extract_entities",
            chunks=chunks,
            tenant_id=tenant_id,
            source_id=source_id,
        )

        log.info("parse_document.completed", chunk_count=len(chunks))
        return {"chunk_count": len(chunks), "source_id": source_id}

    except Exception as e:
        log.error("parse_document.failed", error=str(e), exc_info=True)
        await update_source_status(source_id, "failed", str(e))
        raise  # ARQ will retry
```

### `cascade_delete_source`

```python
async def cascade_delete_source(
    ctx: Ctx,
    *,
    source_id: str,
    tenant_id: str,
) -> dict:
    log = logger.bind(tenant_id=tenant_id, source_id=source_id, job="cascade_delete")
    log.info("cascade_delete.started")

    # Order is critical: storage first, then indices, then metadata
    service = DeletionService()

    # Step 1: Delete raw file from Supabase Storage
    await service.delete_from_storage(tenant_id, source_id)
    log.info("cascade_delete.storage_done")

    # Step 2: Delete all Qdrant points with this source_id
    await service.delete_from_qdrant(tenant_id, source_id)
    log.info("cascade_delete.qdrant_done")

    # Step 3: Delete Neo4j nodes + relationships
    await service.delete_from_neo4j(tenant_id, source_id)
    log.info("cascade_delete.neo4j_done")

    # Step 4: Delete PostgreSQL records
    await service.delete_from_postgres(source_id, tenant_id)
    log.info("cascade_delete.postgres_done")

    log.info("cascade_delete.completed")
    return {"source_id": source_id, "status": "deleted"}
```

---

## Job Status Updates (SSE Pattern)

Jobs publish progress via Redis pub/sub. The API's SSE endpoint subscribes.

```python
# src/workers/utils.py
import json
import redis.asyncio as aioredis
from src.core.config import settings

async def publish_progress(
    source_id: str,
    progress_pct: int,
    message: str,
    status: str = "active",
) -> None:
    """Publish job progress to Redis channel for SSE consumers."""
    r = await aioredis.from_url(settings.REDIS_URL)
    payload = json.dumps({
        "progress_pct": progress_pct,
        "message": message,
        "status": status,
    })
    await r.publish(f"job:progress:{source_id}", payload)

# In API route (SSE endpoint):
# src/api/routes/ingest.py
from sse_starlette.sse import EventSourceResponse

@router.get("/stream/{source_id}")
async def stream_progress(
    source_id: str,
    token: str,                            # EventSource can't set headers
    user: dict = Depends(verify_token_query_param),
):
    async def event_generator():
        r = await aioredis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"job:progress:{source_id}")
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield {"data": message["data"].decode()}
                data = json.loads(message["data"])
                if data.get("status") in ("completed", "failed"):
                    break

    return EventSourceResponse(event_generator())
```

---

## Graceful Shutdown (SIGTERM Handling)

ARQ handles SIGTERM gracefully by default:
- Stops accepting new jobs
- Allows running jobs to complete (up to `job_timeout`)
- On Railway: rolling deploys send SIGTERM, then SIGKILL after 30s grace period

```python
# WorkerSettings — ensure jobs finish within Railway's shutdown window
class WorkerSettings:
    job_timeout = 300         # Must be < Railway's SIGKILL grace period
    health_check_interval = 10
    health_check_key = b"arq:health-check"
```

---

## Dead Letter Queue

ARQ moves permanently failed jobs (max_tries exhausted) to a dead letter set in Redis:

```
Redis key: arq:dead-jobs
```

Monitor with:
```python
# Alert if dead queue depth > 0
# See: architecture/06-observability.md for Grafana alert config
```

---

## Local Worker Development

```bash
# Terminal 1: Start infrastructure
docker-compose up postgres redis qdrant

# Terminal 2: Start FastAPI
uv run uvicorn src.api.main:app --reload --port 8000

# Terminal 3: Start ARQ worker
uv run arq src.workers.main.WorkerSettings --watch src/

# The --watch flag reloads the worker on code changes (dev only)
```


---

## Redis App-Layer Caching (Beyond ARQ)

Redis serves two purposes in Ravenbase: job queue (ARQ) and SSE pub/sub. It can also
serve a third purpose: application-layer read caching for data that is expensive to
compute but changes infrequently.

### What to Cache

| Data | Cache key | TTL | Invalidate when |
|---|---|---|---|
| User credits balance | `credits:{user_id}` | 60s | After every credit deduction |
| User tier (free/pro) | `tier:{user_id}` | 300s | On Stripe webhook |
| Graph node count | `graph:count:{user_id}` | 120s | After ingestion completes |

### Cache Pattern (read-through)

```python
# src/services/credit_service.py — example of cached read
async def get_balance(user_id: str, redis: Redis, db: AsyncSession) -> int:
    cache_key = f"credits:{user_id}"

    # Check cache first
    cached = await redis.get(cache_key)
    if cached is not None:
        return int(cached)

    # Cache miss — read from DB
    user = await db.get(User, user_id)
    balance = user.credits_balance

    # Write to cache with TTL
    await redis.setex(cache_key, 60, str(balance))
    return balance

async def deduct(user_id: str, amount: int, redis: Redis, db: AsyncSession) -> None:
    # ... deduct from DB ...
    # Invalidate cache immediately after mutation
    await redis.delete(f"credits:{user_id}")
```

### What NOT to Cache

- Memory/conflict content — too volatile, invalidation is complex
- Search results — each query is unique, caching gives no benefit
- Qdrant results — Qdrant has its own internal caching; don't double-cache

---

## Scheduled CRON Jobs (ARQ)

ARQ supports scheduled tasks via `cron_jobs` in `WorkerSettings`. These run on the
worker process — no separate scheduler required.

```python
# src/workers/main.py — add to WorkerSettings

from arq.connections import RedisSettings
from arq.cron import cron

class WorkerSettings:
    functions = [
        parse_document,
        extract_entities,
        scan_for_conflicts,
        generate_meta_document,
        cascade_delete_user,
        generate_user_export,
        award_referrer_on_first_upload,
        cleanup_cold_data,          # ← STORY-037
    ]

    cron_jobs = [
        cron(
            cleanup_cold_data,
            hour=2,
            minute=0,
            weekday=6,               # 0=Monday ... 6=Sunday
            # Runs every Sunday at 02:00 UTC
            # Low-traffic window; Railway worker is always running
        ),
    ]

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 3
    job_timeout = 300
    keep_result = 3600
```

> **CRON vs enqueue:** CRON jobs are fire-and-forget — they don't return a job_id and
> don't appear in `JobStatus`. Log their progress via structlog only.
>
> **Idempotency:** The `cleanup_cold_data` task queries for users meeting the criteria
> at runtime. Running it twice in one day is safe (already-processed users won't match
> the query again until next week).
