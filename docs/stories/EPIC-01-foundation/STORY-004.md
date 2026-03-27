# STORY-004: ARQ Worker Setup + Health Endpoint

**Epic:** EPIC-01 — Foundation Infrastructure
**Priority:** P0
**Complexity:** Small
**Depends on:** STORY-002, STORY-003
**Type:** Backend
**Repo:** ravenbase-api

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — ARQ worker setup and health endpoint story.

## Component
COMP-01: IngestionPipeline (ARQ queue foundation)

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 3 async jobs >2s)
> 2. `docs/architecture/04-background-jobs.md` — complete ARQ setup: WorkerSettings, enqueue pattern, SIGTERM handling
> 3. `docs/development/00-project-structure.md` — workers/ directory layout
> 4. `docs/architecture/02-database-schema.md` — JobStatus model (for tracking job state in PostgreSQL)

---

## User Story
As a developer, I want the ARQ job queue worker running locally so that I can enqueue and process background jobs in future stories.

## Context
- ARQ setup: `architecture/04-background-jobs.md` — WorkerSettings, task patterns, SSE pub/sub
- Project structure: `development/00-project-structure.md` — workers/ directory
- Job status model: `architecture/02-database-schema.md` — `job_statuses` table

## Acceptance Criteria
- [ ] AC-1: `src/workers/main.py` exists with `WorkerSettings` class configured for ARQ (correct redis_settings, max_jobs, job_timeout)
- [ ] AC-2: `src/workers/utils.py` has `publish_progress()` for Redis pub/sub SSE and `update_job_status()` for PostgreSQL updates
- [ ] AC-3: A stub `hello_world` task exists that logs "hello from worker" with structlog and returns `{"status": "ok"}`
- [ ] AC-4: `make worker` starts the ARQ worker and it connects to Redis successfully (log shows "ARQ worker ready")
- [ ] AC-5: Enqueueing `hello_world` from a Python shell processes successfully and result appears in Redis
- [ ] AC-6: Worker handles SIGTERM gracefully — logs "shutting down", finishes current job, exits cleanly
- [ ] AC-7: `JobStatus` records are updated in PostgreSQL when job status changes (queued → active → completed)

## Technical Notes

### Files to Create
- `src/workers/main.py` — `WorkerSettings` with all task functions registered
- `src/workers/utils.py` — `publish_progress()` and `update_job_status()` utilities
- `Dockerfile.worker` — `CMD ["arq", "src.workers.main.WorkerSettings"]`

### Files to Modify
- `Makefile` — add `worker` target: `uv run arq src.workers.main.WorkerSettings --watch src/`
- `docker-compose.override.yml` — add `worker` service using `Dockerfile.worker`

### Architecture Constraints
- SIGTERM must be handled — ARQ does this by default, but log a warning when graceful shutdown begins
- `max_jobs = 3` (dev), `max_tries = 3`
- All tasks must log at start and end with structlog, including `tenant_id` and `source_id` where available
- `publish_progress()` must be async (uses `aioredis`) — never use sync redis in async task
- `update_job_status()` must open its own DB session (tasks don't share sessions with the API)

### WorkerSettings Pattern
```python
# src/workers/main.py
from arq.connections import RedisSettings
from src.core.config import settings

class WorkerSettings:
    functions = [hello_world]  # Stub for now; add real tasks in later stories
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 600       # 10 min max per job
    keep_result = 3600      # Keep result in Redis for 1 hour
    retry_jobs = True
    max_tries = 3
    health_check_interval = 10
    health_check_key = b"arq:health-check"
```

### publish_progress Pattern
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
    r = await aioredis.from_url(settings.REDIS_URL)
    payload = json.dumps({
        "progress_pct": progress_pct,
        "message": message,
        "status": status,
    })
    await r.publish(f"job:progress:{source_id}", payload)
    await r.aclose()
```

## Definition of Done
- [ ] `make worker` starts worker with log "ARQ worker ready"
- [ ] `hello_world` task can be enqueued from Python shell and processes successfully
- [ ] `make quality` passes (0 errors)

## Testing This Story

```bash
# Start worker:
make worker
# Expected log: "ARQ worker ready" + "Connected to Redis"

# Enqueue test task from Python shell:
uv run python -c "
import asyncio
from arq import create_pool
from arq.connections import RedisSettings
from src.core.config import settings

async def main():
    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    job = await pool.enqueue_job('hello_world')
    print(f'Enqueued: {job.job_id}')

asyncio.run(main())
"

# Watch worker terminal — expected output:
# hello_world.started
# hello from worker
# hello_world.completed
```

**Passing result:** Worker starts, `hello_world` job processes and logs correctly. `make quality` passes.

---

## Agent Implementation Brief

```
Implement STORY-004: ARQ Worker Setup.

Read first:
1. CLAUDE.md (architecture rules — RULE 3: operations >2s use ARQ queue)
2. docs/architecture/04-background-jobs.md (WorkerSettings, publish_progress pattern, SIGTERM handling)
3. docs/development/00-project-structure.md (workers/ directory layout)
4. docs/architecture/02-database-schema.md (JobStatus model)
5. docs/stories/EPIC-01-foundation/STORY-004.md (this file)

Key constraints:
- ARQ WorkerSettings.functions must list all task functions
- publish_progress() uses aioredis (async), not sync redis
- update_job_status() opens its own DB session per call
- All task functions must use structlog (no print())
- SIGTERM is handled by ARQ automatically — just ensure job_timeout < Railway grace period

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
git add -A && git commit -m "feat(ravenbase): STORY-004 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-004"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-004
git add docs/stories/epics.md && git commit -m "docs: mark STORY-004 complete"
```
