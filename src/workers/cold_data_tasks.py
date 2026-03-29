# src/workers/cold_data_tasks.py
"""ARQ CRON task: cleanup_cold_data — cold data lifecycle (STORY-037).

Scheduled: Sunday 02:00 UTC (see WorkerSettings.cron_jobs in main.py).
Runs Phase 1 (warning at day 150) + Phase 2 (purge at day 180) in one invocation.
Uses ColdDataService for all business logic.
"""

from datetime import UTC, datetime

import structlog

from src.api.dependencies.db import async_session_factory
from src.services.cold_data_service import ColdDataService

logger = structlog.get_logger()


async def cleanup_cold_data(ctx: dict) -> dict:  # type: ignore[type-arg]  # noqa: ARG001
    """CRON entrypoint for cold-data lifecycle.

    Returns summary dict: warnings_sent, purges_executed, errors, duration_ms.
    """
    log = logger.bind(job="cleanup_cold_data")
    log.info("cold_data.run_start")
    start = datetime.now(UTC)

    svc = ColdDataService()
    warnings_sent = 0
    purges_executed = 0
    errors = 0

    async with async_session_factory() as db:
        try:
            warnings_sent = await svc.send_inactivity_warnings(db)
        except Exception as exc:
            log.error("cold_data.warnings_phase_failed", error=str(exc))
            errors += 1

        try:
            purges_executed = await svc.purge_inactive_users(db)
        except Exception as exc:
            log.error("cold_data.purge_phase_failed", error=str(exc))
            errors += 1

    duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
    log.info(
        "cold_data.run_complete",
        warnings_sent=warnings_sent,
        purges_executed=purges_executed,
        errors=errors,
        duration_ms=duration_ms,
    )
    return {"warnings_sent": warnings_sent, "purges_executed": purges_executed, "errors": errors}
