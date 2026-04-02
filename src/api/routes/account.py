# src/api/routes/account.py
from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import async_session_factory, get_db
from src.schemas.account import (
    AccountDeleteResponse,
    ModelPreferenceUpdate,
    NotificationPreferencesUpdate,
)
from src.schemas.export import ExportQueuedResponse, ExportRequest, ExportStatusResponse
from src.schemas.referral import ApplyReferralRequest, ReferralResponse
from src.services.referral_service import ReferralService
from src.services.user_settings_service import UserSettingsService

router = APIRouter(prefix="/v1/account", tags=["account"])
users_router = APIRouter(prefix="/v1/users", tags=["users"])
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


@router.get("/referral", response_model=ReferralResponse)
async def get_referral_info(
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ReferralResponse:
    """Return the current user's referral code, URL, and stats (AC-8).

    Used by Settings → Referrals page.
    """
    return await ReferralService().get_referral_info(db, user["user_id"])


@router.post("/apply-referral")
async def apply_referral_code(
    body: ApplyReferralRequest,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Apply a referral code to the authenticated user's account (AC-2, AC-3, AC-10).

    Awards the referee +200 signup bonus immediately.
    Silently ignores invalid codes (not an error to the user).
    """
    await ReferralService().apply_referral_code(
        db,
        referee_user_id=user["user_id"],
        raw_referral_code=body.referral_code,
    )
    return {"status": "applied"}


@router.post("/export", status_code=202, response_model=ExportQueuedResponse)
async def start_export(
    request: Request,
    body: ExportRequest,
    user: dict = Depends(require_user),  # noqa: B008
) -> ExportQueuedResponse:
    """Enqueue data export job. Rate limited to 1 per 24h per user (AC-2).

    Returns 202 immediately with job_id. Client polls /export/status for progress.
    """
    user_id = user["user_id"]
    log = logger.bind(user_id=user_id)

    # Check rate limit via Redis before enqueuing
    redis = request.app.state.redis
    cooldown_key = f"export:cooldown:{user_id}"
    ttl_bytes = await redis.exists(cooldown_key)
    if ttl_bytes:
        ttl = await redis.ttl(cooldown_key)
        raise HTTPException(
            status_code=429,
            detail={
                "code": "EXPORT_RATE_LIMITED",
                "retry_after_seconds": max(ttl, 0),
            },
        )

    # Enqueue ARQ job
    job = await request.app.state.arq_pool.enqueue_job(
        "generate_user_export",
        user_id=user_id,
        format=body.format,
    )
    job_id = job.job_id if job else f"export:{user_id}"

    # Store job metadata in JobStatus table
    async with async_session_factory() as session:
        from src.models.job_status import JobStatus  # noqa: PLC0415

        status = JobStatus(
            id=job_id,
            user_id=user_id,
            job_type="export",
            status="queued",
        )
        session.add(status)
        await session.commit()

    log.info("export.started", job_id=job_id, format=body.format)
    return ExportQueuedResponse(job_id=job_id, status="queued")


@router.get("/export/status", response_model=ExportStatusResponse)
async def get_export_status(
    job_id: str,
    user: dict = Depends(require_user),  # noqa: B008
) -> ExportStatusResponse:
    """Return export job status and download URL if ready (AC-7)."""
    user_id = user["user_id"]

    async with async_session_factory() as session:
        import json as json_lib  # noqa: PLC0415

        from sqlmodel import select  # noqa: PLC0415

        from src.models.job_status import JobStatus  # noqa: PLC0415

        result_db = await session.exec(
            select(JobStatus).where(
                JobStatus.user_id == user_id,
                JobStatus.id == job_id,
                JobStatus.job_type == "export",
            )
        )
        job_status = result_db.first()

    if job_status is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Export job not found"},
        )

    # Parse result data from message JSON field
    result_data = {}
    if job_status.message:
        try:
            result_data = json_lib.loads(job_status.message)
        except Exception:
            pass

    return ExportStatusResponse(
        status=job_status.status or "idle",
        job_id=job_id,
        download_url=result_data.get("download_url") if result_data else None,
        progress=result_data.get("progress", 0) if result_data else 0,
        error=result_data.get("error") if result_data else None,
    )


# ---------------------------------------------------------------------------
# GET /v1/users/me — current user profile with is_admin flag (ADMIN-002)
# ---------------------------------------------------------------------------


@users_router.get("/me")
async def get_current_user(
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Return current user profile including is_admin flag.

    is_admin is computed from ADMIN_USER_IDS env var — no DB field needed.
    has_completed_onboarding is computed by checking for profile existence.
    """
    from sqlmodel import select as _select  # noqa: PLC0415

    from src.core.config import settings  # noqa: PLC0415
    from src.models.profile import SystemProfile as Profile  # noqa: PLC0415
    from src.models.user import User  # noqa: PLC0415

    user_id = user["user_id"]
    admin_ids = {u.strip() for u in settings.ADMIN_USER_IDS.split(",") if u.strip()}
    is_admin = user_id in admin_ids

    db_user = await db.get(User, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    # Compute has_completed_onboarding from profile existence
    profile_result = await db.exec(_select(Profile).where(Profile.user_id == user_id).limit(1))
    has_completed_onboarding = profile_result.first() is not None

    return {
        "id": db_user.id,
        "email": db_user.email,
        "display_name": db_user.display_name,
        "tier": db_user.tier,
        "credits_balance": db_user.credits_balance,
        "preferred_model": db_user.preferred_model,
        "is_admin": is_admin,
        "has_completed_onboarding": has_completed_onboarding,
    }


@users_router.post("/me/complete-onboarding")
async def complete_onboarding(
    _user: dict = Depends(require_user),  # noqa: B008
) -> dict:
    """Mark onboarding as complete for the current user.

    No-op — onboarding completion is tracked by profile existence.
    Frontend calls this after the onboarding wizard completes.
    """
    return {"status": "ok"}
