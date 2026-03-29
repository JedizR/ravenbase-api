# tests/integration/api/test_cold_data_lifecycle.py
"""Integration tests for STORY-037: Cold Data Lifecycle — Inactivity Archival."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.data_retention_log import DataRetentionLog
from src.models.user import User
from src.services.cold_data_service import ColdDataService
from src.services.deletion_service import (
    _POSTGRES_CONTENT_STATEMENTS,
    _POSTGRES_DELETE_STATEMENTS,
)
from src.workers.main import WorkerSettings

# ── DataRetentionLog sanity ──────────────────────────────────────────────────


def test_retention_log_warning_fields():
    log = DataRetentionLog(user_id="u1", event_type="warning_sent", days_inactive=155)
    assert log.sources_deleted == 0
    assert log.qdrant_vectors_deleted == 0


def test_retention_log_purge_fields():
    log = DataRetentionLog(
        user_id="u1", event_type="data_purged", days_inactive=183, sources_deleted=5
    )
    assert log.sources_deleted == 5


# ── AC-11 regression: content statements exclude users row ───────────────────


def test_content_statements_never_include_users_table():
    """Regression: purge must never delete the users row."""
    for stmt in _POSTGRES_CONTENT_STATEMENTS:
        assert "FROM users" not in stmt, f"Forbidden: {stmt}"


def test_gdpr_statements_include_users_table():
    """GDPR deletion must still delete the users row."""
    assert any("FROM users" in s for s in _POSTGRES_DELETE_STATEMENTS)
    # users row must be last
    assert "users" in _POSTGRES_DELETE_STATEMENTS[-1]


# ── AC-14: purge failure means no is_archived ───────────────────────────────


@pytest.mark.asyncio
async def test_purge_step_failure_leaves_user_not_archived(mocker):
    user = User(
        id="u_fail",
        email="fail@x.com",
        tier="free",
        is_archived=False,
        notify_account_deletion=True,
        last_active_at=datetime.now(UTC) - timedelta(days=185),
        referral_code="FAILFAIL",
        credits_balance=100,
    )
    db = AsyncMock()
    user_r = MagicMock()
    user_r.all.return_value = [user]
    cnt_r = MagicMock()
    cnt_r.one.return_value = 3
    db.exec = AsyncMock(side_effect=[user_r, cnt_r])
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    deletion = MagicMock()
    deletion.delete_storage_by_tenant = AsyncMock(side_effect=Exception("S3 down"))
    mocker.patch("src.services.cold_data_service.settings", ADMIN_USER_IDS="")

    svc = ColdDataService(deletion_service=deletion)
    count = await svc.purge_inactive_users(db)

    assert count == 0
    assert user.is_archived is False
    db.rollback.assert_called_once()
    db.add.assert_not_called()  # no DataRetentionLog written on failure


# ── AC-12: credits zeroed after purge ───────────────────────────────────────


@pytest.mark.asyncio
async def test_purge_zeros_credits_balance(mocker):
    user = User(
        id="u_credits",
        email="c@x.com",
        tier="free",
        is_archived=False,
        notify_account_deletion=True,
        last_active_at=datetime.now(UTC) - timedelta(days=190),
        referral_code="CRED1234",
        credits_balance=500,
    )
    db = AsyncMock()
    user_r = MagicMock()
    user_r.all.return_value = [user]
    cnt_r = MagicMock()
    cnt_r.one.return_value = 2
    db.exec = AsyncMock(side_effect=[user_r, cnt_r])
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    deletion = MagicMock()
    for m in (
        "delete_storage_by_tenant",
        "delete_qdrant_by_tenant",
        "delete_neo4j_by_tenant",
        "delete_content_by_tenant",
    ):
        setattr(deletion, m, AsyncMock())

    mocker.patch("src.services.cold_data_service.settings", ADMIN_USER_IDS="")
    await ColdDataService(deletion_service=deletion).purge_inactive_users(db)

    assert user.credits_balance == 0
    assert user.is_archived is True


# ── AC-4: WorkerSettings CRON schedule ──────────────────────────────────────


def test_cron_job_schedule_is_sunday_0200():
    from arq.cron import CronJob  # noqa: PLC0415

    from src.workers.cold_data_tasks import cleanup_cold_data  # noqa: PLC0415

    job = WorkerSettings.cron_jobs[0]
    assert isinstance(job, CronJob)
    assert job.coroutine is cleanup_cold_data
    assert job.hour == 2
    assert job.minute == 0
    assert job.weekday == 6
