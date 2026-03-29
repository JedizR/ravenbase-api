# src/services/cold_data_service.py
"""ColdDataService: STORY-037 cold-data lifecycle business logic."""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func
from sqlmodel import select as sm_select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings
from src.models.data_retention_log import DataRetentionLog
from src.models.source import Source
from src.models.user import User
from src.services.base import BaseService
from src.services.deletion_service import DeletionService
from src.services.email_service import EmailService

logger = structlog.get_logger()

_WARNING_DAYS = 150
_PURGE_DAYS = 180
BATCH_SIZE = 50


def _admin_ids() -> set[str]:
    return {uid.strip() for uid in settings.ADMIN_USER_IDS.split(",") if uid.strip()}


class ColdDataService(BaseService):
    def __init__(
        self,
        deletion_service: DeletionService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self._deletion = deletion_service
        self._email = email_service

    def _get_deletion(self) -> DeletionService:
        if self._deletion is None:
            self._deletion = DeletionService()
        return self._deletion

    def _get_email(self) -> EmailService:
        if self._email is None:
            self._email = EmailService()
        return self._email

    async def send_inactivity_warnings(self, db: AsyncSession) -> int:
        """Phase 1: warn Free users inactive 150-179 days. Returns count sent."""
        log = logger.bind(action="cold_data.warnings")
        now = datetime.now(UTC)
        cutoff_150 = now - timedelta(days=_WARNING_DAYS)
        cutoff_180 = now - timedelta(days=_PURGE_DAYS)
        admin_ids = _admin_ids()
        sent = 0

        stmt = (
            sm_select(User)
            .where(
                User.tier == "free",
                User.is_archived.is_(False),  # type: ignore[attr-defined]
                User.notify_account_deletion.is_(True),  # type: ignore[attr-defined]
                User.last_active_at <= cutoff_150,  # type: ignore[operator]
                User.last_active_at > cutoff_180,  # type: ignore[operator]
            )
            .limit(BATCH_SIZE)
        )
        result = await db.exec(stmt)
        candidates = result.all()
        log.info("cold_data.warnings.candidates", count=len(candidates))

        for user in candidates:
            ulog = log.bind(tenant_id=user.id)
            if user.id in admin_ids:
                ulog.info("cold_data.skip_admin")
                continue

            dedup = await db.exec(
                sm_select(DataRetentionLog).where(
                    DataRetentionLog.user_id == user.id,
                    DataRetentionLog.event_type == "warning_sent",
                    DataRetentionLog.created_at > cutoff_180,
                )
            )
            if dedup.first():
                ulog.info("cold_data.warnings.already_sent")
                continue

            try:
                await self._get_email().send_account_deletion_warning(
                    to_email=user.email,
                    display_name=user.display_name,
                    user_id=user.id,
                )
            except Exception as exc:
                ulog.error("cold_data.warning_email_failed", error=str(exc))
                continue  # AC-7: non-fatal — skip this user, try next

            days_inactive = (now - user.last_active_at).days  # type: ignore[operator]
            db.add(
                DataRetentionLog(
                    user_id=user.id,
                    event_type="warning_sent",
                    days_inactive=days_inactive,
                )
            )
            await db.commit()
            ulog.info("cold_data.warnings.sent", days_inactive=days_inactive)
            sent += 1

        log.info("cold_data.warnings.complete", sent=sent)
        return sent

    async def purge_inactive_users(self, db: AsyncSession) -> int:
        """Phase 2: purge data for Free users inactive >= 180 days. Returns count purged."""
        log = logger.bind(action="cold_data.purge")
        now = datetime.now(UTC)
        cutoff_180 = now - timedelta(days=_PURGE_DAYS)
        admin_ids = _admin_ids()
        purged = 0

        stmt = (
            sm_select(User)
            .where(
                User.tier == "free",
                User.is_archived.is_(False),  # type: ignore[attr-defined]
                User.last_active_at <= cutoff_180,  # type: ignore[operator]
            )
            .limit(BATCH_SIZE)
        )
        result = await db.exec(stmt)
        candidates = result.all()
        log.info("cold_data.purge.candidates", count=len(candidates))

        deletion_svc = self._get_deletion()

        for user in candidates:
            ulog = log.bind(tenant_id=user.id)
            if user.id in admin_ids:
                ulog.info("cold_data.skip_admin")
                continue

            src_count_result = await db.exec(
                sm_select(func.count()).select_from(Source).where(Source.user_id == user.id)
            )
            src_count: int = src_count_result.one()

            try:
                await deletion_svc.delete_storage_by_tenant(user.id)
                ulog.info("cold_data.purge.step_complete", step="storage")
                await deletion_svc.delete_qdrant_by_tenant(user.id)
                ulog.info("cold_data.purge.step_complete", step="qdrant")
                await deletion_svc.delete_neo4j_by_tenant(user.id)
                ulog.info("cold_data.purge.step_complete", step="neo4j")
                await deletion_svc.delete_content_by_tenant(user.id, db)
                ulog.info("cold_data.purge.step_complete", step="postgres_content")
            except Exception as exc:
                ulog.error("cold_data.purge_step_failed", error=str(exc))
                await db.rollback()
                continue

            user.is_archived = True
            user.credits_balance = 0
            days_inactive = (now - user.last_active_at).days  # type: ignore[operator]
            db.add(user)
            db.add(
                DataRetentionLog(
                    user_id=user.id,
                    event_type="data_purged",
                    days_inactive=days_inactive,
                    sources_deleted=src_count,
                    qdrant_vectors_deleted=0,  # AC-13: deletion service doesn't return counts
                    neo4j_nodes_deleted=0,
                    storage_bytes_freed=0,
                )
            )
            await db.commit()
            ulog.info(
                "cold_data.purge.archived", sources_deleted=src_count, days_inactive=days_inactive
            )
            purged += 1

        log.info("cold_data.purge.complete", purged=purged)
        return purged
