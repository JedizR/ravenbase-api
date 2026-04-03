import json
from datetime import datetime

import redis.asyncio as aioredis
import structlog

from src.api.dependencies.db import async_session_factory
from src.core.config import settings
from src.models.job_status import JobStatus

logger = structlog.get_logger()


async def publish_progress(
    source_id: str,
    progress_pct: int,
    message: str,
    status: str = "active",
) -> None:
    """Publish job progress to Redis pub/sub channel for SSE consumers."""
    log = logger.bind(source_id=source_id, progress_pct=progress_pct, status=status)
    log.debug("publish_progress.sending")
    r = await aioredis.from_url(settings.REDIS_URL)
    try:
        payload = json.dumps({"progress_pct": progress_pct, "message": message, "status": status})
        await r.publish(f"job:progress:{source_id}", payload)
    finally:
        await r.aclose()


async def update_job_status(
    job_id: str,
    status: str,
    progress_pct: int = 0,
    message: str | None = None,
) -> None:
    """Update JobStatus record in PostgreSQL. Opens its own session per call."""
    log = logger.bind(job_id=job_id, status=status)
    async with async_session_factory() as session:
        job = await session.get(JobStatus, job_id)
        if job is None:
            log.warning("update_job_status.not_found")
            return
        job.status = status
        job.progress_pct = progress_pct
        job.message = message
        job.updated_at = datetime.utcnow()
        session.add(job)
        await session.commit()
        log.info("update_job_status.saved", progress_pct=progress_pct)
