# src/services/profile_service.py
"""Service layer for system profile CRUD — RULE 1 compliance."""

from __future__ import annotations

import uuid

import structlog
from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.profile import SystemProfile
from src.schemas.profile import ProfileCreate, ProfileUpdate
from src.services.base import BaseService

logger = structlog.get_logger()


class ProfileService(BaseService):
    """All profile CRUD operations. Routes delegate here; no DB in route handlers."""

    async def list_profiles(self, db: AsyncSession, user_id: str) -> list[SystemProfile]:
        results = await db.exec(select(SystemProfile).where(SystemProfile.user_id == user_id))
        return list(results.all())

    async def create_profile(
        self, db: AsyncSession, user_id: str, profile_in: ProfileCreate
    ) -> SystemProfile:
        log = logger.bind(user_id=user_id, profile_name=profile_in.name)
        if profile_in.is_default:
            stmt = (
                select(SystemProfile)
                .where(SystemProfile.user_id == user_id)
                .where(SystemProfile.is_default)
            )
            existing_defaults = (await db.exec(stmt)).all()
            for p in existing_defaults:
                p.is_default = False
            db.add_all(existing_defaults)

        profile = SystemProfile(
            user_id=user_id,
            name=profile_in.name,
            description=profile_in.description,
            icon=profile_in.icon,
            color=profile_in.color,
            is_default=profile_in.is_default,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        log.info("profiles.created", profile_id=str(profile.id))
        return profile

    async def update_profile(
        self,
        db: AsyncSession,
        profile_id: uuid.UUID,
        user_id: str,
        profile_in: ProfileUpdate,
    ) -> SystemProfile:
        log = logger.bind(user_id=user_id, profile_id=str(profile_id))
        stmt = select(SystemProfile).where(
            SystemProfile.id == profile_id,
            SystemProfile.user_id == user_id,
        )
        profile = (await db.exec(stmt)).one_or_none()
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "PROFILE_NOT_FOUND", "message": "Profile not found"},
            )

        update_data = profile_in.model_dump(exclude_unset=True)
        if not update_data:
            return profile

        if update_data.get("is_default") is True:
            stmt = (
                select(SystemProfile)
                .where(SystemProfile.user_id == user_id)
                .where(SystemProfile.id != profile_id)
                .where(SystemProfile.is_default)
            )
            existing_defaults = (await db.exec(stmt)).all()
            for p in existing_defaults:
                p.is_default = False
            db.add_all(existing_defaults)

        for key, value in update_data.items():
            setattr(profile, key, value)

        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        log.info("profiles.updated", profile_id=str(profile_id))
        return profile

    async def delete_profile(self, db: AsyncSession, profile_id: uuid.UUID, user_id: str) -> None:
        log = logger.bind(user_id=user_id, profile_id=str(profile_id))
        stmt = select(SystemProfile).where(
            SystemProfile.id == profile_id,
            SystemProfile.user_id == user_id,
        )
        profile = (await db.exec(stmt)).one_or_none()
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "PROFILE_NOT_FOUND", "message": "Profile not found"},
            )

        all_profiles = (
            await db.exec(select(SystemProfile).where(SystemProfile.user_id == user_id))
        ).all()
        if len(all_profiles) <= 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "CANNOT_DELETE_LAST_PROFILE",
                    "message": "Cannot delete the last remaining profile",
                },
            )

        await db.delete(profile)
        await db.commit()
        log.info("profiles.deleted", profile_id=str(profile_id))
