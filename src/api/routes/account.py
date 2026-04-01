# src/api/routes/account.py
from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
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


@router.get("/notification-preferences")
async def get_notification_preferences(
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Get the user's notification preference flags."""
    db_user = await UserSettingsService().get_notification_preferences(db, user["user_id"])
    return {
        "notify_welcome": db_user.notify_welcome,
        "notify_low_credits": db_user.notify_low_credits,
        "notify_ingestion_complete": db_user.notify_ingestion_complete,
    }


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


@router.post("/notification-prefs/test/{email_type}")
async def send_test_notification_email(
    email_type: Literal["welcome", "low_credits", "ingestion_complete"],
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Send a test email of the specified type to the authenticated user's email.

    This endpoint is used by the Settings → Notifications page to let users
    preview each email template before it fires for real.
    """
    from src.models.user import User  # noqa: PLC0415
    from src.services.email_service import EmailService  # noqa: PLC0415

    log = logger.bind(user_id=user["user_id"], email_type=email_type)

    # Fetch user record to get email
    user_record = await db.get(User, user["user_id"])
    if not user_record:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    email_service = EmailService()

    try:
        if email_type == "welcome":
            await email_service.send_welcome(
                email=user_record.email,
                first_name=user_record.email.split("@", maxsplit=1)[0],
                notify=True,
            )
        elif email_type == "low_credits":
            await email_service.send_low_credits(
                email=user_record.email,
                balance=100,
                plan_limit=1000,
                notify=True,
            )
        elif email_type == "ingestion_complete":
            await email_service.send_ingestion_complete(
                email=user_record.email,
                filename="test-document.pdf",
                node_count=42,
                notify=True,
            )
        log.info("account.test_email_sent", email_type=email_type)
        return {"status": "sent"}
    except Exception as exc:
        log.error("account.test_email_failed", email_type=email_type, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={"code": "EMAIL_SEND_FAILED", "message": "Failed to send test email"},
        ) from exc
