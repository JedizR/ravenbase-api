# src/api/routes/webhooks.py
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from src.api.dependencies.db import get_db
from src.core.config import settings
from src.models.user import User

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
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
                "svix-id": svix_id,
                "svix-timestamp": svix_timestamp,
                "svix-signature": svix_signature,
            },
        )
    except WebhookVerificationError:
        logger.warning("webhook.invalid_signature")
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_SIGNATURE", "message": "Webhook signature verification failed"},
        )

    event_type = payload.get("type")
    log = logger.bind(event_type=event_type)

    if event_type == "user.created":
        await _handle_user_created(payload["data"], db, log)

    return {"status": "ok"}


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
    )
    db.add(user)
    try:
        await db.commit()
    except Exception as exc:
        log.error("webhook.user_created_db_error", user_id=clerk_user_id, error=str(exc))
        raise
    log.info("webhook.user_created", user_id=clerk_user_id, email=email)
