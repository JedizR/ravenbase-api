from arq import cron
from arq.connections import RedisSettings

from src.core.config import settings
from src.workers.cold_data_tasks import cleanup_cold_data
from src.workers.conflict_tasks import scan_for_conflicts
from src.workers.deletion_tasks import cascade_delete_account
from src.workers.export_tasks import generate_user_export
from src.workers.graph_tasks import graph_extraction
from src.workers.ingestion_tasks import ingest_text, parse_document
from src.workers.metadoc_tasks import generate_meta_document


class WorkerSettings:
    """ARQ WorkerSettings. Add real tasks in later stories."""

    functions = [
        parse_document,
        ingest_text,
        graph_extraction,
        scan_for_conflicts,
        generate_meta_document,
        cascade_delete_account,
        cleanup_cold_data,
        generate_user_export,
    ]
    cron_jobs = [
        cron(cleanup_cold_data, hour=2, minute=0, weekday=6),  # Sunday 02:00 UTC
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = settings.MAX_CONCURRENT_INGEST_JOBS
    job_timeout = 600  # 10 min max per job; must be < Railway SIGKILL grace period
    keep_result = 3600  # Keep result in Redis for 1 hour
    retry_jobs = True
    max_tries = 3
    health_check_interval = 10
    health_check_key = b"arq:health-check"
