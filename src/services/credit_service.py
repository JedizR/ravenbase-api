# src/services/credit_service.py
import uuid as _uuid

import structlog
from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.errors import ErrorCode
from src.models.credit import CreditTransaction
from src.models.user import User
from src.services.base import BaseService

logger = structlog.get_logger()


class CreditService(BaseService):
    """Atomic credit mutations. All writes use SELECT FOR UPDATE."""

    async def deduct(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        operation: str,
        reference_id: _uuid.UUID | None = None,
    ) -> CreditTransaction:
        """Atomically deduct `amount` credits from user.

        Raises 402 INSUFFICIENT_CREDITS if balance < amount.
        Uses SELECT FOR UPDATE to prevent concurrent overdraw.
        """
        log = logger.bind(user_id=user_id, amount=amount, operation=operation)

        user = (await db.exec(select(User).where(User.id == user_id).with_for_update())).one()

        if user.credits_balance < amount:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": ErrorCode.INSUFFICIENT_CREDITS,
                    "message": f"Need {amount}, have {user.credits_balance}",
                },
            )

        user.credits_balance -= amount
        txn = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            balance_after=user.credits_balance,
            operation=operation,
            reference_id=reference_id,
        )
        db.add(user)
        db.add(txn)
        await db.commit()
        log.info("credit_service.deducted", balance_after=user.credits_balance)
        return txn

    async def add_credits(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        operation: str,
        reference_id: _uuid.UUID | None = None,
    ) -> CreditTransaction:
        """Atomically add `amount` credits to user.

        Uses SELECT FOR UPDATE for consistency with deduct().
        """
        log = logger.bind(user_id=user_id, amount=amount, operation=operation)

        user = (await db.exec(select(User).where(User.id == user_id).with_for_update())).one()

        user.credits_balance += amount
        txn = CreditTransaction(
            user_id=user_id,
            amount=amount,
            balance_after=user.credits_balance,
            operation=operation,
            reference_id=reference_id,
        )
        db.add(user)
        db.add(txn)
        await db.commit()
        log.info("credit_service.added", balance_after=user.credits_balance)
        return txn

    async def get_balance(self, db: AsyncSession, user_id: str) -> int:
        """Return current credits_balance for user_id."""
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={"code": ErrorCode.TENANT_NOT_FOUND, "message": "User not found"},
            )
        return user.credits_balance

    async def get_recent_transactions(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
    ) -> list[CreditTransaction]:
        """Return the most recent credit transactions for user_id, newest first."""
        from sqlmodel import desc  # noqa: PLC0415

        result = await db.exec(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(desc(CreditTransaction.created_at))
            .limit(limit)
        )
        return list(result.all())
