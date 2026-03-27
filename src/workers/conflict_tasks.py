# src/workers/conflict_tasks.py
from __future__ import annotations

import structlog

from src.services.conflict_service import ConflictService

logger = structlog.get_logger()


async def scan_for_conflicts(
    ctx: dict,  # type: ignore[type-arg]  # noqa: ARG001
    *,
    source_id: str,
    tenant_id: str,
) -> dict:  # type: ignore[type-arg]
    """Scan new source chunks against existing memories for contradictions.

    Enqueued automatically by graph_extraction after graph write completes.
    Does not update source status (source is already COMPLETED).
    On any failure: returns error dict without re-raising (prevents ARQ retry).
    Conflict detection is best-effort: a missed scan is non-critical and retrying
    could cause duplicate Conflict records if the first attempt partially succeeded.
    """
    log = logger.bind(source_id=source_id, tenant_id=tenant_id, job="scan_for_conflicts")
    log.info("scan_for_conflicts.started")

    try:
        service = ConflictService()
        stats = await service.scan_and_create_conflicts(
            source_id=source_id,
            tenant_id=tenant_id,
        )
        log.info("scan_for_conflicts.completed", **stats)
        return {"status": "ok", "source_id": source_id, **stats}
    except Exception as exc:
        log.error("scan_for_conflicts.failed", error=str(exc), exc_info=True)
        return {"status": "error", "source_id": source_id, "error": str(exc)}
