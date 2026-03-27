# src/api/routes/conflict.py
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.schemas.common import PaginatedResponse
from src.schemas.conflict import (
    ConflictResponse,
    ResolveRequest,
    ResolveResponse,
    UndoResponse,
)
from src.services.conflict_service import ConflictService

router = APIRouter(prefix="/v1/conflicts", tags=["conflicts"])


@router.get("", response_model=PaginatedResponse[ConflictResponse])
async def list_conflicts(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PaginatedResponse[ConflictResponse]:
    """List conflicts for the authenticated user, newest first."""
    svc = ConflictService()
    return await svc.list_conflicts(user["user_id"], status, page, page_size, db)


@router.post("/{conflict_id}/resolve", response_model=ResolveResponse)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    body: ResolveRequest,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ResolveResponse:
    """Resolve a pending conflict (ACCEPT_NEW, KEEP_OLD, or CUSTOM)."""
    svc = ConflictService()
    return await svc.resolve_conflict(
        str(conflict_id), user["user_id"], body.action, body.custom_text, db
    )


@router.post("/{conflict_id}/undo", response_model=UndoResponse)
async def undo_resolution(
    conflict_id: uuid.UUID,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> UndoResponse:
    """Undo a conflict resolution within the 30-second window."""
    svc = ConflictService()
    return await svc.undo_resolution(str(conflict_id), user["user_id"], db)
