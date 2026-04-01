# src/services/user_service.py
"""User lifecycle mutations called from webhook handlers — RULE 1 compliance."""

from __future__ import annotations

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.user import User
from src.services.base import BaseService

logger = structlog.get_logger()


class UserService(BaseService):
    """Tier and subscription lifecycle mutations. Used by webhook handlers."""

    async def update_user_tier(self, db: AsyncSession, user_id: str, tier: str) -> None:
        log = logger.bind(user_id=user_id, tier=tier)
        result = await db.exec(select(User).where(User.id == user_id))
        user = result.first()
        if user is None:
            log.error("user_service.user_not_found_for_tier_upgrade", user_id=user_id)
            raise ValueError(f"User {user_id} not found")
        user.tier = tier
        db.add(user)
        await db.commit()
        log.info("user_service.tier_updated")

    async def revert_subscription_to_free(self, db: AsyncSession, stripe_customer_id: str) -> None:
        log = logger.bind(stripe_customer_id=stripe_customer_id)
        result = await db.exec(select(User).where(User.stripe_customer_id == stripe_customer_id))
        user = result.first()
        if user is None:
            log.warning("user_service.no_user_for_stripe_customer")
            return
        previous_tier = user.tier
        user.tier = "free"
        db.add(user)
        await db.commit()
        log.info("user_service.subscription_reverted_to_free", previous_tier=previous_tier)
