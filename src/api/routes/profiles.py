# src/api/routes/profiles.py
"""CRUD endpoints for system profiles."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.models.profile import SystemProfile
from src.schemas.profile import (
    PaginatedProfileResponse,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])
logger = structlog.get_logger()


@router.get("", response_model=PaginatedProfileResponse)
async def list_profiles(
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PaginatedProfileResponse:
    """List all profiles for the authenticated user."""
    user_id: str = user["user_id"]
    log = logger.bind(user_id=user_id)

    stmt = select(SystemProfile).where(SystemProfile.user_id == user_id)
    results = await db.exec(stmt)
    profiles = list(results.all())

    log.info("profiles.list_fetched", count=len(profiles))
    return PaginatedProfileResponse(
        items=[ProfileResponse.model_validate(p) for p in profiles],
        total=len(profiles),
        has_more=False,
    )


@router.post("", response_model=ProfileResponse, status_code=201)
async def create_profile(
    profile_in: ProfileCreate,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ProfileResponse:
    """Create a new profile for the authenticated user."""
    user_id: str = user["user_id"]
    log = logger.bind(user_id=user_id, profile_name=profile_in.name)

    # If this profile is set as default, unset other defaults first
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
    return ProfileResponse.model_validate(profile)


@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    profile_in: ProfileUpdate,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ProfileResponse:
    """Partially update a profile. All fields are optional."""
    user_id: str = user["user_id"]
    log = logger.bind(user_id=user_id, profile_id=str(profile_id))

    stmt = select(SystemProfile).where(
        SystemProfile.id == profile_id,
        SystemProfile.user_id == user_id,
    )
    results = await db.exec(stmt)
    profile = results.one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Profile not found"},
        )

    update_data = profile_in.model_dump(exclude_unset=True)
    if not update_data:
        return ProfileResponse.model_validate(profile)

    # If setting as default, unset other defaults first
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
    return ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: uuid.UUID,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    """Delete a profile. Cannot delete the last remaining profile."""
    user_id: str = user["user_id"]
    log = logger.bind(user_id=user_id, profile_id=str(profile_id))

    stmt = select(SystemProfile).where(
        SystemProfile.id == profile_id,
        SystemProfile.user_id == user_id,
    )
    results = await db.exec(stmt)
    profile = results.one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Profile not found"},
        )

    # Prevent deleting the last profile
    all_stmt = select(SystemProfile).where(SystemProfile.user_id == user_id)
    all_profiles = (await db.exec(all_stmt)).all()
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
    return Response(status_code=204)
