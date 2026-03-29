# src/api/routes/admin.py
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.admin import get_arq_pool, require_admin
from src.api.dependencies.db import get_db
from src.schemas.admin import (
    AdminStatsResponse,
    AdminTransactionOut,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserOut,
    CreditAdjustRequest,
    CreditAdjustResponse,
    ToggleActiveRequest,
    ToggleActiveResponse,
)
from src.services.admin_service import AdminService

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    q: str | None = Query(default=None, description="Email search (case-insensitive)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: dict = Depends(require_admin),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminUserListResponse:
    """List all users with optional email search. Admin only."""
    users, total = await AdminService().list_users(db, q, page, page_size)
    return AdminUserListResponse(
        users=[AdminUserOut.model_validate(u) for u in users],
        total=total,
        page=page,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
async def get_user_detail(
    user_id: str,
    _admin: dict = Depends(require_admin),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AdminUserDetailResponse:
    """Get full user profile with recent transactions and source count. Admin only."""
    user, transactions, source_count = await AdminService().get_user_detail(db, user_id)
    return AdminUserDetailResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        tier=user.tier,
        credits_balance=user.credits_balance,
        is_active=user.is_active,
        created_at=user.created_at,
        last_active_at=user.last_active_at,
        referral_code=user.referral_code,
        recent_transactions=[AdminTransactionOut.model_validate(t) for t in transactions],
        source_count=source_count,
    )


@router.post("/credits/adjust", response_model=CreditAdjustResponse)
async def adjust_credits(
    body: CreditAdjustRequest,
    _admin: dict = Depends(require_admin),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> CreditAdjustResponse:
    """Adjust a user's credit balance. Positive adds, negative removes. Admin only."""
    new_balance, txn_id = await AdminService().adjust_credits(
        db, body.user_id, body.amount, body.reason
    )
    return CreditAdjustResponse(new_balance=new_balance, transaction_id=txn_id)


@router.post("/users/{user_id}/toggle-active", response_model=ToggleActiveResponse)
async def toggle_active(
    user_id: str,
    body: ToggleActiveRequest,
    _admin: dict = Depends(require_admin),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ToggleActiveResponse:
    """Set user active/inactive status. Admin only."""
    is_active = await AdminService().toggle_active(db, user_id, body.active)
    return ToggleActiveResponse(is_active=is_active)


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    _admin: dict = Depends(require_admin),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
    arq_pool=Depends(get_arq_pool),  # noqa: B008
) -> AdminStatsResponse:
    """Platform-wide metrics including Redis LLM spend. Admin only."""
    redis_key = f"llm:daily_spend:{date.today().isoformat()}"
    raw = await arq_pool.get(redis_key)
    llm_spend_usd = float(raw) if raw else 0.0
    return await AdminService().get_stats(db, llm_spend_usd)
