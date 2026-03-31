# src/api/routes/billing.py
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.schemas.billing import (
    CheckoutSessionResponse,
    CreateCheckoutSessionRequest,
    PortalSessionResponse,
)
from src.services.billing_service import BillingService

router = APIRouter(prefix="/v1/billing", tags=["billing"])
logger = structlog.get_logger()


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    body: CreateCheckoutSessionRequest,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout session for a tier subscription.

    Returns a checkout_url — the frontend must redirect the user there.
    Session is created server-side to keep STRIPE_SECRET_KEY off the client.
    """
    user_id: str = user["user_id"]
    email: str = user["email"]
    log = logger.bind(user_id=user_id, tier=body.tier, period=body.period)

    svc = BillingService()
    checkout_url = await svc.create_checkout_session(db, user_id, email, body.tier, body.period)
    log.info("billing.checkout_session_returned")
    return CheckoutSessionResponse(checkout_url=checkout_url)


@router.post("/create-portal-session", response_model=PortalSessionResponse)
async def create_portal_session(
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PortalSessionResponse:
    """Create a Stripe Customer Portal session.

    Returns portal_url — the frontend must redirect the user there.
    Only meaningful for users who have an active Stripe subscription.
    """
    user_id: str = user["user_id"]
    email: str = user["email"]
    log = logger.bind(user_id=user_id)

    svc = BillingService()
    portal_url = await svc.create_portal_session(db, user_id, email)
    log.info("billing.portal_session_returned")
    return PortalSessionResponse(portal_url=portal_url)
