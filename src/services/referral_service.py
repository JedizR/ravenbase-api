# src/services/referral_service.py
from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings
from src.core.errors import ErrorCode
from src.models.referral import ReferralTransaction
from src.models.user import User
from src.schemas.referral import ReferralResponse
from src.services.base import BaseService
from src.services.credit_service import CreditService

logger = structlog.get_logger()

REFERRAL_SIGNUP_BONUS = 200
REFERRAL_FIRST_UPLOAD_BONUS = 200
MONTHLY_CAP = 50
APP_BASE_URL = settings.APP_BASE_URL.rstrip("/")


class ReferralService(BaseService):
    """Referral logic: apply codes, award bonuses, track transactions."""

    async def _count_referrals_this_month(
        self,
        db: AsyncSession,
        referrer_user_id: str,
    ) -> int:
        """Return count of first_upload ReferralTransaction records this calendar month."""
        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

        result = await db.exec(
            select(ReferralTransaction).where(
                ReferralTransaction.referrer_user_id == referrer_user_id,
                ReferralTransaction.trigger_event == "first_upload",
                ReferralTransaction.created_at >= month_start,
            )
        )
        return len(list(result.all()))

    async def _count_referrals_by_user(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> tuple[int, int, int]:
        """Return (total, pending, credits_earned) for user as referrer."""
        # Total successful (first_upload completed)
        total_result = await db.exec(
            select(ReferralTransaction).where(
                ReferralTransaction.referrer_user_id == user_id,
                ReferralTransaction.trigger_event == "first_upload",
            )
        )
        all_referrals = list(total_result.all())
        total = len(all_referrals)

        # Credits earned: sum of referrer_credits_awarded
        credits_earned = sum(r.referrer_credits_awarded for r in all_referrals)

        # Pending: referee's referral_reward_claimed is still False
        pending = 0
        referee_ids = [r.referee_user_id for r in all_referrals]
        if referee_ids:
            referee_result = await db.exec(
                select(User).where(User.id.in_(referee_ids))  # type: ignore[attr-defined]
            )
            referee_map = {u.id: u for u in referee_result.all()}
            pending = sum(
                1
                for r in all_referrals
                if (
                    (referee := referee_map.get(r.referee_user_id))
                    and not referee.referral_reward_claimed
                )
            )

        return total, pending, credits_earned

    async def apply_referral_code(
        self,
        db: AsyncSession,
        referee_user_id: str,
        raw_referral_code: str,
    ) -> None:
        """Link referee to referrer and award referee +200 signup bonus.

        AC-2: Sets referred_by_user_id on referee user.
        AC-3: Awards referee +200 signup_referral_bonus immediately.
        AC-10: Normalizes code to uppercase before DB lookup.
        AC-6: Creates ReferralTransaction with trigger_event="signup".
        """
        log = logger.bind(referee_user_id=referee_user_id)

        # Normalize to uppercase (AC-10)
        referral_code = raw_referral_code.strip().upper()

        if not referral_code:
            log.warning("referral_service.apply_empty_code")
            return

        # Look up referrer by referral_code (case-insensitive via uppercase)
        result = await db.exec(select(User).where(User.referral_code == referral_code))
        referrer = result.first()

        if referrer is None:
            log.info("referral_service.code_not_found", referral_code=referral_code)
            return  # Silently ignored per AC-2

        if referrer.id == referee_user_id:
            log.info("referral_service.self_referral_skipped")
            return

        referee_user = await db.get(User, referee_user_id)
        if referee_user is None:
            log.error("referral_service.referee_not_found", referee_user_id=referee_user_id)
            return

        if referee_user.referred_by_user_id is not None:
            log.info("referral_service.already_referred", referee_user_id=referee_user_id)
            return

        # Set referrer on referee user (AC-2)
        referee_user.referred_by_user_id = referrer.id
        db.add(referee_user)

        # Award referee +200 signup bonus (AC-3)
        credit_svc = CreditService()
        await credit_svc.add_credits(
            db,
            referee_user_id,
            REFERRAL_SIGNUP_BONUS,
            "signup_referral_bonus",
        )

        # Record transaction (AC-6)
        txn = ReferralTransaction(
            referrer_user_id=referrer.id,
            referee_user_id=referee_user_id,
            referrer_credits_awarded=0,
            referee_credits_awarded=REFERRAL_SIGNUP_BONUS,
            trigger_event="signup",
        )
        db.add(txn)

        await db.commit()
        log.info(
            "referral_service.signup_bonus_awarded",
            referrer_user_id=referrer.id,
            referee_user_id=referee_user_id,
            bonus=REFERRAL_SIGNUP_BONUS,
        )

    async def award_referrer_on_first_upload(
        self,
        db: AsyncSession,
        referee_user_id: str,
    ) -> None:
        """Award referrer +200 when referee completes first source upload.

        AC-4: Awards referrer +200 referral_reward on first Source creation.
        AC-5: Sets referral_reward_claimed=True on referee user.
        AC-6: Creates ReferralTransaction with trigger_event="first_upload".
        AC-7: Skips if referrer already has >=50 first_upload rewards this month.
        """
        log = logger.bind(referee_user_id=referee_user_id)

        referee_user = await db.get(User, referee_user_id)
        if referee_user is None:
            log.warning(
                "referral_service.referee_user_not_found",
                referee_user_id=referee_user_id,
            )
            return

        referrer_user_id = referee_user.referred_by_user_id
        if referrer_user_id is None:
            log.info("referral_service.no_referrer_skipped", referee_user_id=referee_user_id)
            return

        if referee_user.referral_reward_claimed:
            log.info("referral_service.reward_already_claimed", referee_user_id=referee_user_id)
            return  # Idempotency guard (AC-5)

        # Monthly cap check (AC-7) — before awarding
        current_month_count = await self._count_referrals_this_month(db, referrer_user_id)
        if current_month_count >= MONTHLY_CAP:
            log.info(
                "referral_service.monthly_cap_reached",
                referrer_user_id=referrer_user_id,
                current_month_count=current_month_count,
            )
            return

        # Get referrer with FOR UPDATE lock
        referrer_result = await db.exec(
            select(User).where(User.id == referrer_user_id).with_for_update()
        )
        referrer = referrer_result.one_or_none()

        if referrer is None:
            log.warning(
                "referral_service.referrer_user_not_found",
                referrer_user_id=referrer_user_id,
            )
            return

        # Award referrer +200 (AC-4)
        credit_svc = CreditService()
        await credit_svc.add_credits(
            db,
            referrer_user_id,
            REFERRAL_FIRST_UPLOAD_BONUS,
            "referral_reward",
        )

        # Record transaction (AC-6)
        txn = ReferralTransaction(
            referrer_user_id=referrer_user_id,
            referee_user_id=referee_user_id,
            referrer_credits_awarded=REFERRAL_FIRST_UPLOAD_BONUS,
            referee_credits_awarded=0,
            trigger_event="first_upload",
        )
        db.add(txn)

        # Mark reward claimed — idempotency guard (AC-5)
        referee_user.referral_reward_claimed = True
        db.add(referee_user)

        await db.commit()
        log.info(
            "referral_service.first_upload_reward_awarded",
            referrer_user_id=referrer_user_id,
            referee_user_id=referee_user_id,
            bonus=REFERRAL_FIRST_UPLOAD_BONUS,
        )

    async def get_referral_info(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> ReferralResponse:
        """Return referral stats for the settings page (AC-8)."""
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": ErrorCode.TENANT_NOT_FOUND,
                    "message": "User not found",
                },
            )

        referral_code = user.referral_code
        referral_url = f"{APP_BASE_URL}/register?ref={referral_code}"

        total, pending, credits_earned = await self._count_referrals_by_user(db, user_id)
        current_month_count = await self._count_referrals_this_month(db, user_id)

        return ReferralResponse(
            referral_code=referral_code,
            referral_url=referral_url,
            total_referrals=total,
            pending_referrals=pending,
            credits_earned=credits_earned,
            current_month_count=current_month_count,
            monthly_cap=MONTHLY_CAP,
        )
