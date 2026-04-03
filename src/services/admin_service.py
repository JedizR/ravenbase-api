# src/services/admin_service.py
from datetime import UTC, date, datetime, time

import structlog
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings
from src.core.errors import ErrorCode, raise_404
from src.models.credit import CreditTransaction
from src.models.meta_document import MetaDocument
from src.models.source import Source
from src.models.user import User
from src.schemas.admin import AdminStatsResponse
from src.services.base import BaseService

logger = structlog.get_logger()


class AdminService(BaseService):
    """Admin operations: user management, credit adjustments, platform stats."""

    async def list_users(
        self,
        db: AsyncSession,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        """Return paginated user list with optional email search.

        Returns (users, total_count).
        q filters by email ilike '%q%'. Empty/None q returns all users.
        """
        log = logger.bind(q=q, page=page, page_size=page_size)

        count_stmt = select(func.count()).select_from(User)
        rows_stmt = (
            select(User)
            .order_by(User.created_at.desc())  # type: ignore[arg-type]
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        if q:
            filter_clause = User.email.ilike(f"%{q}%")  # type: ignore[union-attr]
            count_stmt = count_stmt.where(filter_clause)
            rows_stmt = rows_stmt.where(filter_clause)

        total = (await db.exec(count_stmt)).one()
        users = list((await db.exec(rows_stmt)).all())

        log.info("admin.list_users", total=total, returned=len(users))
        return users, total

    async def get_user_detail(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> tuple[User, list[CreditTransaction], int]:
        """Return user + last 20 credit transactions + source count.

        Raises 404 if user not found.
        """
        from sqlmodel import desc  # noqa: PLC0415

        log = logger.bind(user_id=user_id)

        user = await db.get(User, user_id)
        if user is None:
            raise_404(ErrorCode.TENANT_NOT_FOUND, f"User {user_id} not found")

        transactions = list(
            (
                await db.exec(
                    select(CreditTransaction)
                    .where(CreditTransaction.user_id == user_id)
                    .order_by(desc(CreditTransaction.created_at))
                    .limit(20)
                )
            ).all()
        )

        source_count = (
            await db.exec(select(func.count(Source.id)).where(Source.user_id == user_id))  # type: ignore[arg-type]
        ).one()

        log.info("admin.get_user_detail", source_count=source_count, txn_count=len(transactions))
        return user, transactions, source_count

    async def adjust_credits(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        reason: str,
    ) -> tuple[int, int]:
        """Adjust user credits by signed amount. Admin can produce negative balances.

        Returns (new_balance, transaction_id).
        amount is stored verbatim in CreditTransaction.amount (negative = deduction).
        reason is logged via structlog but not stored (no field on CreditTransaction).
        """
        log = logger.bind(user_id=user_id, amount=amount, reason=reason)

        user = (
            await db.exec(select(User).where(User.id == user_id).with_for_update())
        ).one_or_none()

        if user is None:
            raise_404(ErrorCode.TENANT_NOT_FOUND, f"User {user_id} not found")

        balance_before = user.credits_balance
        user.credits_balance += amount
        user.updated_at = datetime.utcnow()

        txn = CreditTransaction(
            user_id=user_id,
            amount=amount,
            balance_after=user.credits_balance,
            operation="admin_adjustment",
        )
        db.add(user)
        db.add(txn)
        await db.commit()
        await db.refresh(txn)

        log.info(
            "admin.credits_adjusted",
            balance_before=balance_before,
            balance_after=user.credits_balance,
            txn_id=txn.id,
        )
        return user.credits_balance, txn.id

    async def toggle_active(
        self,
        db: AsyncSession,
        user_id: str,
        active: bool,
    ) -> bool:
        """Set user.is_active. Returns new is_active value. Raises 404 if not found."""
        log = logger.bind(user_id=user_id, active=active)

        user = (
            await db.exec(select(User).where(User.id == user_id).with_for_update())
        ).one_or_none()

        if user is None:
            raise_404(ErrorCode.TENANT_NOT_FOUND, f"User {user_id} not found")

        user.is_active = active
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()

        log.info("admin.toggle_active", is_active=user.is_active)
        return user.is_active

    async def get_stats(
        self,
        db: AsyncSession,
        llm_spend_usd: float,
    ) -> AdminStatsResponse:
        """Return platform aggregate metrics.

        llm_spend_usd is pre-fetched from Redis by the route handler.
        Source uses ingested_at; MetaDocument uses generated_at; User uses created_at/last_active_at.
        """
        today_start = datetime.combine(date.today(), time.min).replace(tzinfo=UTC)

        total_users = (await db.exec(select(func.count()).select_from(User))).one()
        active_today = (
            await db.exec(
                select(func.count()).select_from(User).where(User.last_active_at >= today_start)  # type: ignore[operator]
            )
        ).one()
        new_today = (
            await db.exec(
                select(func.count()).select_from(User).where(User.created_at >= today_start)
            )
        ).one()
        pro_users = (
            await db.exec(select(func.count()).select_from(User).where(User.tier == "pro"))
        ).one()
        sources_today = (
            await db.exec(
                select(func.count()).select_from(Source).where(Source.ingested_at >= today_start)
            )
        ).one()
        metadocs_today = (
            await db.exec(
                select(func.count())
                .select_from(MetaDocument)
                .where(MetaDocument.generated_at >= today_start)
            )
        ).one()

        logger.info("admin.stats_fetched", total_users=total_users, llm_spend_usd=llm_spend_usd)
        return AdminStatsResponse(
            total_users=total_users,
            active_today=active_today,
            new_today=new_today,
            pro_users=pro_users,
            daily_llm_spend_usd=llm_spend_usd,
            llm_spend_cap_usd=settings.MAX_DAILY_LLM_SPEND_USD,
            sources_today=sources_today,
            metadocs_today=metadocs_today,
        )
