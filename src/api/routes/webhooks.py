# src/api/routes/webhooks.py
import uuid
from datetime import UTC, datetime

import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from src.api.dependencies.db import get_db
from src.core.config import settings
from src.models.user import User
from src.services.credit_service import CreditService
from src.services.user_service import UserService

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:
    """Receive Clerk webhook events and react to user lifecycle changes.

    Only handles `user.created` for now. All other event types are silently
    acknowledged (200 OK) to prevent Clerk from retrying them indefinitely.

    Rejects unsigned requests with 400 to prevent spoofed webhook calls.
    """
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")

    if not all([svix_id, svix_timestamp, svix_signature]):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_WEBHOOK", "message": "Missing svix signature headers"},
        )

    body = await request.body()

    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        payload = wh.verify(
            body,
            {
                "svix-id": svix_id or "",
                "svix-timestamp": svix_timestamp or "",
                "svix-signature": svix_signature or "",
            },
        )
    except WebhookVerificationError:
        logger.warning("webhook.invalid_signature")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SIGNATURE",
                "message": "Webhook signature verification failed",
            },
        ) from None
    except Exception as exc:
        logger.error("webhook.verification_error", error=str(exc), error_type=type(exc).__name__)
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VERIFICATION_ERROR",
                "message": f"Webhook verification error: {type(exc).__name__}",
            },
        ) from None

    event_type = payload.get("type")
    log = logger.bind(event_type=event_type)

    try:
        if event_type == "user.created":
            await _handle_user_created(payload["data"], db, log)
        elif event_type == "user.deleted":
            await _handle_user_deleted(payload["data"], request, log)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("webhook.handler_error", event_type=event_type, error=str(exc), error_type=type(exc).__name__)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "WEBHOOK_HANDLER_ERROR",
                "message": f"Failed to process {event_type}: {type(exc).__name__}: {str(exc)[:200]}",
            },
        ) from None

    return {"status": "ok"}


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict:  # type: ignore[type-arg]
    """Receive Stripe webhook events.

    Handles:
      - checkout.session.completed: tier upgrade OR credit top-up (by session_type metadata)
      - customer.subscription.deleted: revert User.tier to 'free'

    Idempotency: checks Redis key stripe:event:{event_id} before processing.
    Sets the key ONLY after a successful DB write (AC-11, AC-12).
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_WEBHOOK", "message": "Missing stripe-signature header"},
        )

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        logger.warning("stripe_webhook.invalid_signature")
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_SIGNATURE", "message": "Stripe signature verification failed"},
        ) from None

    event_id: str = event["id"]
    event_type: str = event.get("type", "")
    log = logger.bind(event_id=event_id, event_type=event_type)

    # Idempotency: return 200 immediately if already processed (AC-11)
    redis = request.app.state.redis
    idempotency_key = f"stripe:event:{event_id}"
    if await redis.exists(idempotency_key):
        log.info("stripe_webhook.duplicate_skipped")
        return {"status": "already_processed"}  # Must be 200, not 4xx — Stripe retries on non-2xx

    # Process event
    handled = False
    try:
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            session_type = session.get("metadata", {}).get("session_type", "credit_topup")
            if session_type == "tier_upgrade":
                await _handle_tier_upgrade(session, db, log)
            else:
                await _handle_credit_topup(session, db, log)
            handled = True
        elif event_type == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await _handle_subscription_deleted(subscription, db, log)
            handled = True
    except Exception as exc:
        log.error("stripe_webhook.processing_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Webhook processing failed") from exc

    # Mark processed ONLY after successful DB write (AC-12)
    # Only set key for event types we actually handle — don't suppress retries for future handlers
    if handled:
        await redis.setex(idempotency_key, 86400, "1")  # TTL: 24 hours
    return {"status": "processed"}


async def _handle_tier_upgrade(
    session: dict,  # type: ignore[type-arg]
    db: AsyncSession,
    log: structlog.stdlib.BoundLogger,
) -> None:
    """checkout.session.completed with session_type=tier_upgrade → set User.tier."""
    user_id: str = session["metadata"]["user_id"]
    tier: str = session["metadata"]["tier"]
    if tier not in {"pro", "team"}:
        log.error("stripe_webhook.invalid_tier", tier=tier)
        raise ValueError(f"Invalid tier value in Stripe metadata: {tier!r}")
    await UserService().update_user_tier(db, user_id, tier)
    log.info("stripe_webhook.tier_upgraded", user_id=user_id, tier=tier)


async def _handle_credit_topup(
    session: dict,  # type: ignore[type-arg]
    db: AsyncSession,
    log: structlog.stdlib.BoundLogger,
) -> None:
    """checkout.session.completed with session_type=credit_topup → add credits."""
    user_id: str = session["metadata"]["user_id"]
    credits: int = int(session["metadata"]["credits"])
    if credits <= 0:
        raise ValueError(f"Invalid credits value in Stripe metadata: {credits}")
    credit_svc = CreditService()
    await credit_svc.add_credits(db, user_id, credits, "stripe_topup")
    log.info("stripe_webhook.credits_added", user_id=user_id, credits=credits)


async def _handle_subscription_deleted(
    subscription: dict,  # type: ignore[type-arg]
    db: AsyncSession,
    log: structlog.stdlib.BoundLogger,
) -> None:
    """customer.subscription.deleted → revert User.tier to 'free'."""
    customer_id: str = subscription["customer"]
    await UserService().revert_subscription_to_free(db, customer_id)
    log.info("stripe_webhook.subscription_deleted", stripe_customer_id=customer_id)


async def _handle_user_deleted(
    data: dict,  # type: ignore[type-arg]
    request: Request,
    log: structlog.stdlib.BoundLogger,
) -> None:
    """user.deleted → enqueue cascade deletion. Clerk identity is already gone.

    Uses the same ARQ job as DELETE /v1/account. The deletion task handles
    a missing Clerk user gracefully (last step, logs and continues).
    """
    clerk_user_id: str = data["id"]
    log = log.bind(user_id=clerk_user_id)
    job_id = f"gdpr:{clerk_user_id}"
    await request.app.state.arq_pool.enqueue_job(
        "cascade_delete_account",
        user_id=clerk_user_id,
        _job_id=job_id,
    )
    log.info("webhook.user_deleted_gdpr_enqueued", user_id=clerk_user_id, job_id=job_id)


async def _handle_user_created(
    data: dict,
    db: AsyncSession,
    log: structlog.stdlib.BoundLogger,
) -> None:
    clerk_user_id: str = data["id"]

    existing = await db.get(User, clerk_user_id)
    if existing is not None:
        log.info("webhook.user_already_exists", user_id=clerk_user_id)
        return

    # Resolve primary email
    email_addresses = data.get("email_addresses", [])
    primary_id = data.get("primary_email_address_id")
    email = next(
        (e["email_address"] for e in email_addresses if e["id"] == primary_id),
        email_addresses[0]["email_address"] if email_addresses else "",
    )

    if not email:
        log.warning("webhook.user_created_no_email", user_id=clerk_user_id)
        return

    first_name = data.get("first_name") or ""
    last_name = data.get("last_name") or ""
    display_name = f"{first_name} {last_name}".strip() or None
    avatar_url = data.get("image_url")

    # Generate referral code: first 8 hex chars of a fresh UUID, uppercase
    referral_code = str(uuid.uuid4()).replace("-", "")[:8].upper()

    user = User(
        id=clerk_user_id,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
        referral_code=referral_code,
        last_active_at=datetime.now(UTC),
    )
    db.add(user)
    try:
        await db.commit()
    except Exception as exc:
        log.error("webhook.user_created_db_error", user_id=clerk_user_id, error=str(exc))
        raise
    log.info("webhook.user_created", user_id=clerk_user_id, email=email)
    # Write signup_bonus credit transaction (AC-7)
    credit_svc = CreditService()
    await credit_svc.add_credits(db, clerk_user_id, 500, "signup_bonus")
    log.info("webhook.signup_bonus_added", user_id=clerk_user_id)
