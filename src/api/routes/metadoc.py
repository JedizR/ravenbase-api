# src/api/routes/metadoc.py
from __future__ import annotations

import json

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import column, desc
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies.auth import require_user, verify_token_query_param
from src.api.dependencies.db import get_db
from src.core.config import settings
from src.models.meta_document import MetaDocument
from src.schemas.metadoc import GenerateRequest, GenerateResponse, MetaDocSummary
from src.services.metadoc_service import MetadocService

router = APIRouter(prefix="/v1/metadoc", tags=["metadoc"])
logger = structlog.get_logger()


@router.get("", response_model=list[MetaDocSummary])
async def list_meta_documents(
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100, alias="pageSize"),
) -> list[MetaDocSummary]:
    """List the user's Meta-Documents, most recent first."""
    log = logger.bind(tenant_id=user["user_id"])

    offset = (page - 1) * page_size
    result = await db.exec(
        select(MetaDocument)
        .where(MetaDocument.user_id == user["user_id"])
        .order_by(desc(column("generated_at")))
        .offset(offset)
        .limit(page_size)
    )
    docs = result.all()

    log.info("metadoc.list", count=len(docs), page=page)
    return [
        MetaDocSummary(
            id=doc.id,
            title=doc.title,
            original_prompt=doc.original_prompt,
            credits_consumed=doc.credits_consumed,
            generated_at=doc.generated_at,
        )
        for doc in docs
    ]


@router.post("/generate", response_model=GenerateResponse, status_code=202)
async def generate_meta_document(
    request: Request,
    body: GenerateRequest,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> GenerateResponse:
    """Enqueue Meta-Document generation. Returns job_id immediately.

    Raises 402 if user has insufficient credits (checked before enqueueing).
    Credits are deducted by the worker AFTER successful generation.
    """
    svc = MetadocService()
    return await svc.handle_generate(
        prompt=body.prompt,
        profile_id=str(body.profile_id) if body.profile_id else None,
        model_alias=body.model,
        tenant_id=user["user_id"],
        arq_pool=request.app.state.arq_pool,
        db=db,
    )


@router.get("/stream/{job_id}")
async def stream_meta_document(
    job_id: str,
    user: dict = Depends(verify_token_query_param),  # noqa: B008
) -> EventSourceResponse:
    """SSE stream for Meta-Document generation progress.

    EventSource cannot set custom headers, so the Clerk JWT is passed as
    ?token= query parameter and validated by verify_token_query_param.

    Events: {"type": "token", "content": "..."} during generation.
    Final:  {"type": "done", "doc_id": uuid, "credits_consumed": int}
         or {"type": "error", "message": "..."}

    Stream closes automatically when type is "done" or "error".
    """
    log = logger.bind(job_id=job_id, tenant_id=user["user_id"])

    async def event_generator():
        r = aioredis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        channel = f"metadoc:stream:{job_id}"
        try:
            await pubsub.subscribe(channel)
            log.info("sse.metadoc.subscribed", channel=channel)
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                raw = message["data"]
                payload = raw.decode() if isinstance(raw, bytes) else raw
                yield {"data": payload}
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    log.warning("sse.metadoc.invalid_json", raw=payload)
                    continue
                if data.get("type") in ("done", "error"):
                    log.info("sse.metadoc.closing", event_type=data.get("type"))
                    break
        finally:
            await pubsub.unsubscribe(channel)
            await r.aclose()
            log.info("sse.metadoc.unsubscribed", channel=channel)

    return EventSourceResponse(event_generator())
