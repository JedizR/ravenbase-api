import json

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies.auth import require_user, verify_token_query_param
from src.api.dependencies.db import get_db
from src.core.config import settings
from src.models.source import Source
from src.schemas.ingest import (
    ImportPromptResponse,
    SourceListResponse,
    TextIngestRequest,
    UploadResponse,
)
from src.services.ingestion_service import IngestionService

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])

logger = structlog.get_logger()


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_file(
    request: Request,
    file: UploadFile,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UploadResponse:
    """Enqueue a file for background ingestion. Returns job_id immediately."""
    content = await file.read()
    svc = IngestionService()
    return await svc.handle_upload(
        content=content,
        filename=file.filename or "upload",
        tenant_id=user["user_id"],
        tier=user.get("tier", "free"),
        arq_pool=request.app.state.arq_pool,
        db=db,
    )


@router.post("/text", response_model=UploadResponse, status_code=202)
async def ingest_text(
    request: Request,
    body: TextIngestRequest,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UploadResponse:
    """Enqueue plain text for background ingestion. Returns job_id immediately."""
    svc = IngestionService()
    return await svc.handle_text_ingest(
        content=body.content,
        profile_id=str(body.profile_id) if body.profile_id else None,
        tags=body.tags,
        tenant_id=user["user_id"],
        arq_pool=request.app.state.arq_pool,
        db=db,
    )


@router.get("/sources", response_model=SourceListResponse)
async def list_sources(
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SourceListResponse:
    """List all sources for the authenticated user, newest first."""
    stmt = (
        select(Source)
        .where(Source.user_id == user["user_id"])
        .order_by(Source.ingested_at.desc())  # type: ignore[union-attr]
        .offset(offset)
        .limit(limit)
    )
    results = await db.exec(stmt)
    sources = list(results.all())

    count_stmt = select(Source).where(Source.user_id == user["user_id"])
    count_results = await db.exec(count_stmt)
    total = len(list(count_results.all()))

    return SourceListResponse(items=sources, total=total)


@router.get("/stream/{source_id}")
async def stream_progress(
    source_id: str,
    user: dict = Depends(verify_token_query_param),  # noqa: B008
) -> EventSourceResponse:
    """Stream ingestion progress events via Server-Sent Events.

    EventSource cannot set custom headers, so the Clerk JWT is passed as
    the ?token= query parameter and validated by verify_token_query_param.

    The stream closes automatically when status is 'completed' or 'failed'.
    Redis pubsub is always unsubscribed in the finally block to prevent leaks.
    """
    log = logger.bind(source_id=source_id, tenant_id=user["user_id"])

    async def event_generator():
        r = await aioredis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        channel = f"job:progress:{source_id}"
        try:
            await pubsub.subscribe(channel)
            log.info("sse.subscribed", channel=channel)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                raw = message["data"]
                payload = raw.decode() if isinstance(raw, bytes) else raw
                yield {"data": payload}
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    log.warning("sse.invalid_json", raw=payload)
                    continue
                if data.get("status") in ("completed", "failed"):
                    log.info("sse.closing", status=data["status"])
                    break
        finally:
            await pubsub.unsubscribe(channel)
            await r.aclose()
            log.info("sse.unsubscribed", channel=channel)

    return EventSourceResponse(event_generator())


@router.get("/import-prompt", response_model=ImportPromptResponse)
async def get_import_prompt(
    profile_id: str | None = None,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
) -> ImportPromptResponse:
    """Return a personalized AI-chat extraction prompt based on the user's Concept nodes.

    Pass ?profile_id=<uuid> to scope concepts to a specific profile.
    New users with no concepts receive a generic prompt — never returns 404.
    """
    svc = IngestionService()
    return await svc.generate_import_prompt(
        tenant_id=user["user_id"],
        profile_id=profile_id,
    )
