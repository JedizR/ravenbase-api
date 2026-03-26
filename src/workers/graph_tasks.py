# src/workers/graph_tasks.py
from __future__ import annotations

import structlog

from src.services.graph_service import GraphService

logger = structlog.get_logger()


async def graph_extraction(
    ctx: dict,  # type: ignore[type-arg]
    *,
    source_id: str,
    tenant_id: str,
) -> dict:  # type: ignore[type-arg]
    """Extract entities from indexed chunks and write Concept/Memory nodes to Neo4j.

    Enqueued automatically by parse_document and ingest_text after indexing completes.
    Source status is already COMPLETED — this task does not update it.
    Chunk failures are logged and skipped; the task itself does not retry on partial failure.
    """
    log = logger.bind(source_id=source_id, tenant_id=tenant_id, job="graph_extraction")
    log.info("graph_extraction.started")

    try:
        service = GraphService()
        stats = await service.extract_and_write(source_id=source_id, tenant_id=tenant_id)
        log.info("graph_extraction.completed", **stats)
        return {"status": "ok", "source_id": source_id, **stats}
    except Exception as exc:
        log.error("graph_extraction.failed", error=str(exc), exc_info=True)
        return {"status": "error", "source_id": source_id, "error": str(exc)}
