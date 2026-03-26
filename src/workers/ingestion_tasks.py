import structlog

logger = structlog.get_logger()


async def process_ingestion(
    _ctx: dict,  # type: ignore[type-arg]
    *,
    source_id: str,
    tenant_id: str,
) -> dict:  # type: ignore[type-arg]
    """Stub task — full parsing pipeline implemented in STORY-006+.

    Receives the source_id and tenant_id, logs start/completion,
    and returns a success dict. Real document parsing (Docling,
    chunking, embedding) will be added in subsequent stories.
    """
    log = logger.bind(source_id=source_id, tenant_id=tenant_id)
    log.info("process_ingestion.started")
    log.info("process_ingestion.completed")
    return {"status": "ok", "source_id": source_id}
