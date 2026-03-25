from arq.connections import RedisSettings

from src.core.config import settings


class WorkerSettings:
    """ARQ WorkerSettings. Tasks registered here as implemented in later stories."""

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions: list = []
    cron_jobs: list = []
    max_jobs = settings.MAX_CONCURRENT_INGEST_JOBS
