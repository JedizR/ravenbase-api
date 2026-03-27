import structlog
from arq.connections import RedisSettings

from src.core.config import settings
from src.workers.conflict_tasks import scan_for_conflicts
from src.workers.graph_tasks import graph_extraction
from src.workers.ingestion_tasks import ingest_text, parse_document
from src.workers.metadoc_tasks import generate_meta_document

logger = structlog.get_logger()


async def hello_world(_ctx: dict) -> dict:  # type: ignore[type-arg]
    """Stub task to verify ARQ worker is running. Returns {"status": "ok"}."""
    log = logger.bind(job="hello_world")
    log.info("hello_world.started")
    log.info("hello from worker")
    log.info("hello_world.completed")
    return {"status": "ok"}


class WorkerSettings:
    """ARQ WorkerSettings. Add real tasks in later stories."""

    functions = [hello_world, parse_document, ingest_text, graph_extraction, scan_for_conflicts, generate_meta_document]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = settings.MAX_CONCURRENT_INGEST_JOBS
    job_timeout = 600  # 10 min max per job; must be < Railway SIGKILL grace period
    keep_result = 3600  # Keep result in Redis for 1 hour
    retry_jobs = True
    max_tries = 3
    health_check_interval = 10
    health_check_key = b"arq:health-check"
