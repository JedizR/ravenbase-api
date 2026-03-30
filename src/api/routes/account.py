# src/api/routes/account.py
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.models.user import User
from src.schemas.account import AccountDeleteResponse

router = APIRouter(prefix="/v1/account", tags=["account"])
logger = structlog.get_logger()

VALID_MODELS = ("claude-haiku-4-5-20251001", "claude-sonnet-4-6")


class ModelPreferenceUpdate(BaseModel):
    preferred_model: str


class NotificationPreferencesUpdate(BaseModel):
    notify_welcome: bool | None = None
    notify_low_credits: bool | None = None
    notify_ingestion_complete: bool | None = None


@router.delete("", response_model=AccountDeleteResponse, status_code=202)
async def delete_account(
    request: Request,
    authorization: str | None = Header(None),
) -> AccountDeleteResponse:
    """Enqueue full account deletion cascade. Returns 202 immediately.

    tenant_id comes exclusively from the validated JWT (require_user).
    The cascade runs in the background: Storage -> Qdrant -> Neo4j -> PostgreSQL -> Clerk.
    SLA: completes within 60 seconds for typical accounts (FR-11-AC-2).
    """
    # Called directly (not via Depends) so tests can patch
    # `src.api.routes.account.require_user` at the module level.
    # FastAPI captures Depends references at decoration time, making them
    # unpatchable; a direct call resolves the name at runtime.
    user = await require_user(request, authorization)
    user_id: str = user["user_id"]
    log = logger.bind(tenant_id=user_id, action="gdpr_deletion")
    log.info("gdpr_deletion.request_received")

    deterministic_job_id = f"gdpr:{user_id}"
    job = await request.app.state.arq_pool.enqueue_job(
        "cascade_delete_account",
        user_id=user_id,
        _job_id=deterministic_job_id,
    )
    # ARQ returns None if the job already exists (deduplication by _job_id)
    job_id = job.job_id if job is not None else deterministic_job_id

    log.info("gdpr_deletion.job_enqueued", job_id=job_id)
    return AccountDeleteResponse(job_id=job_id)


@router.patch("/model-preference")
async def update_model_preference(
    body: ModelPreferenceUpdate,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Update the user's preferred model for generation tasks.

    Valid values: claude-haiku-4-5-20251001, claude-sonnet-4-6
    """
    user_id: str = user["user_id"]
    log = logger.bind(user_id=user_id, preferred_model=body.preferred_model)

    if body.preferred_model not in VALID_MODELS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_MODEL",
                "message": f"preferred_model must be one of: {', '.join(VALID_MODELS)}",
            },
        )

    stmt = select(User).where(User.id == user_id)
    results = await db.exec(stmt)
    db_user = results.one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    db_user.preferred_model = body.preferred_model
    db.add(db_user)
    await db.commit()

    log.info("account.model_preference_updated", preferred_model=body.preferred_model)
    return {"preferred_model": body.preferred_model}


@router.patch("/notification-preferences")
async def update_notification_preferences(
    body: NotificationPreferencesUpdate,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Update the user's notification preference flags.

    All fields are optional — only provided fields are updated.
    """
    user_id: str = user["user_id"]
    log = logger.bind(user_id=user_id)

    stmt = select(User).where(User.id == user_id)
    results = await db.exec(stmt)
    db_user = results.one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.add(db_user)
    await db.commit()

    log.info("account.notification_preferences_updated", fields=list(update_data.keys()))
    return {
        "notify_welcome": db_user.notify_welcome,
        "notify_low_credits": db_user.notify_low_credits,
        "notify_ingestion_complete": db_user.notify_ingestion_complete,
    }
