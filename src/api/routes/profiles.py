# src/api/routes/profiles.py
"""CRUD endpoints for system profiles."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.schemas.profile import (
    PaginatedProfileResponse,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)
from src.services.profile_service import ProfileService

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])
logger = structlog.get_logger()


@router.get("", response_model=PaginatedProfileResponse)
async def list_profiles(
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PaginatedProfileResponse:
    user_id: str = user["user_id"]
    profiles = await ProfileService().list_profiles(db, user_id)
    logger.bind(user_id=user_id).info("profiles.list_fetched", count=len(profiles))
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
    profile = await ProfileService().create_profile(db, user["user_id"], profile_in)
    return ProfileResponse.model_validate(profile)


@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    profile_in: ProfileUpdate,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ProfileResponse:
    profile = await ProfileService().update_profile(db, profile_id, user["user_id"], profile_in)
    return ProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: uuid.UUID,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Response:
    await ProfileService().delete_profile(db, profile_id, user["user_id"])
    return Response(status_code=204)
