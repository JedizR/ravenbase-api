# src/services/user_settings_service.py
"""Service layer for user settings mutations — RULE 1 compliance."""

from __future__ import annotations

import structlog
from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.user import User
from src.services.base import BaseService

logger = structlog.get_logger()

VALID_MODELS = ("claude-haiku-4-5-20251001", "claude-sonnet-4-6")


class UserSettingsService(BaseService):
    """Model preference and notification flag mutations."""

    async def update_model_preference(
        self, db: AsyncSession, user_id: str, preferred_model: str
    ) -> User:
        log = logger.bind(user_id=user_id, preferred_model=preferred_model)
        if preferred_model not in VALID_MODELS:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_MODEL",
                    "message": f"preferred_model must be one of: {', '.join(VALID_MODELS)}",
                },
            )
        result = await db.exec(select(User).where(User.id == user_id))
        user = result.one_or_none()
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            )
        user.preferred_model = preferred_model
        db.add(user)
        await db.commit()
        log.info("account.model_preference_updated")
        return user

    async def get_notification_preferences(self, db: AsyncSession, user_id: str) -> User:
        """Fetch the user's notification preference flags."""
        log = logger.bind(user_id=user_id)
        result = await db.exec(select(User).where(User.id == user_id))
        user = result.one_or_none()
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            )
        log.info("account.notification_preferences_fetched")
        return user

    async def update_notification_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        update_data: dict,  # type: ignore[type-arg]
    ) -> User:
        log = logger.bind(user_id=user_id)
        result = await db.exec(select(User).where(User.id == user_id))
        user = result.one_or_none()
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "USER_NOT_FOUND", "message": "User not found"},
            )
        for key, value in update_data.items():
            setattr(user, key, value)
        db.add(user)
        await db.commit()
        log.info("account.notification_preferences_updated", fields=list(update_data.keys()))
        return user
