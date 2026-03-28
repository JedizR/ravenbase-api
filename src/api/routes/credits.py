# src/api/routes/credits.py
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.schemas.credits import BalanceResponse, CreditTransactionOut
from src.services.credit_service import CreditService

router = APIRouter(prefix="/v1/credits", tags=["credits"])
logger = structlog.get_logger()


@router.get("/balance", response_model=BalanceResponse)
async def get_credits_balance(
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> BalanceResponse:
    """Return current credit balance and last 20 transactions for the authenticated user."""
    user_id: str = user["user_id"]
    log = logger.bind(user_id=user_id)

    svc = CreditService()
    balance = await svc.get_balance(db, user_id)
    transactions = await svc.get_recent_transactions(db, user_id)

    log.info("credits.balance_fetched", balance=balance, txn_count=len(transactions))
    return BalanceResponse(
        balance=balance,
        transactions=[CreditTransactionOut.model_validate(t) for t in transactions],
    )
