# src/api/routes/account.py
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Header, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.schemas.account import (
    AccountDeleteResponse,
    ModelPreferenceUpdate,
    NotificationPreferencesUpdate,
)
from src.services.user_settings_service import UserSettingsService

router = APIRouter(prefix="/v1/account", tags=["account"])
logger = structlog.get_logger()


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
    db_user = await UserSettingsService().update_model_preference(
        db, user["user_id"], body.preferred_model
    )
    return {"preferred_model": db_user.preferred_model}


@router.patch("/notification-preferences")
async def update_notification_preferences(
    body: NotificationPreferencesUpdate,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Update the user's notification preference flags.

    All fields are optional — only provided fields are updated.
    """
    update_data = body.model_dump(exclude_unset=True)
    db_user = await UserSettingsService().update_notification_preferences(
        db, user["user_id"], update_data
    )
    return {
        "notify_welcome": db_user.notify_welcome,
        "notify_low_credits": db_user.notify_low_credits,
        "notify_ingestion_complete": db_user.notify_ingestion_complete,
    }
