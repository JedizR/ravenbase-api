# src/services/billing_service.py
from __future__ import annotations

import stripe
import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings
from src.models.user import User
from src.services.base import BaseService

logger = structlog.get_logger()


def _get_price_id(tier: str, period: str) -> str:
    """Map tier+period to the Stripe Price ID from settings."""
    mapping = {
        ("pro", "monthly"): settings.STRIPE_PRO_MONTHLY_PRICE_ID,
        ("pro", "annual"): settings.STRIPE_PRO_ANNUAL_PRICE_ID,
        ("team", "monthly"): settings.STRIPE_TEAM_MONTHLY_PRICE_ID,
        ("team", "annual"): settings.STRIPE_TEAM_ANNUAL_PRICE_ID,
    }
    price_id = mapping.get((tier, period), "")
    if not price_id:
        raise ValueError(f"No Stripe price ID configured for tier={tier} period={period}")
    return price_id


class BillingService(BaseService):
    def __init__(self) -> None:
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def get_or_create_stripe_customer(
        self,
        db: AsyncSession,
        user_id: str,
        email: str,
    ) -> str:
        """Return existing Stripe customer ID, or create a new one and persist it."""
        result = await db.exec(select(User).where(User.id == user_id))
        user = result.first()
        if user is None:
            raise ValueError(f"User {user_id} not found")

        if user.stripe_customer_id:
            return user.stripe_customer_id

        log = logger.bind(user_id=user_id)
        customer = stripe.Customer.create(email=email, metadata={"user_id": user_id})
        user.stripe_customer_id = customer.id
        db.add(user)
        await db.commit()
        log.info("billing.stripe_customer_created", stripe_customer_id=customer.id)
        return customer.id

    async def create_checkout_session(
        self,
        db: AsyncSession,
        user_id: str,
        email: str,
        tier: str,
        period: str,
    ) -> str:
        """Create a Stripe Checkout session for a tier subscription. Returns checkout URL."""
        price_id = _get_price_id(tier, period)
        customer_id = await self.get_or_create_stripe_customer(db, user_id, email)
        log = logger.bind(user_id=user_id, tier=tier, period=period)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.APP_BASE_URL}/chat?checkout=success",
            cancel_url=f"{settings.APP_BASE_URL}/pricing",
            metadata={
                "user_id": user_id,
                "tier": tier,
                "period": period,
                "session_type": "tier_upgrade",
            },
        )
        log.info("billing.checkout_session_created", session_id=session.id)
        return session.url  # type: ignore[return-value]

    async def create_portal_session(
        self,
        db: AsyncSession,
        user_id: str,
        email: str,
    ) -> str:
        """Create a Stripe Customer Portal session. Returns portal URL."""
        customer_id = await self.get_or_create_stripe_customer(db, user_id, email)
        log = logger.bind(user_id=user_id)

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.APP_BASE_URL}/settings/billing",
        )
        log.info("billing.portal_session_created")
        return session.url
