# tests/unit/workers/test_worker_settings.py
from arq.cron import CronJob

from src.workers.cold_data_tasks import cleanup_cold_data
from src.workers.main import WorkerSettings


def test_has_cron_jobs():
    assert hasattr(WorkerSettings, "cron_jobs")
    assert len(WorkerSettings.cron_jobs) >= 1


def test_cron_is_sunday_0200_utc():
    job = WorkerSettings.cron_jobs[0]
    assert isinstance(job, CronJob)
    assert job.coroutine is cleanup_cold_data
    assert job.hour == 2
    assert job.minute == 0
    assert job.weekday == 6  # Sunday


def test_cleanup_cold_data_in_functions():
    assert cleanup_cold_data in WorkerSettings.functions
