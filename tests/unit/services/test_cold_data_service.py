# tests/unit/services/test_cold_data_service.py
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.models.data_retention_log import DataRetentionLog
from src.models.user import User
from src.services.cold_data_service import ColdDataService


def _free_user(uid="u1", days_inactive=155, notify=True, archived=False) -> User:
    return User(
        id=uid, email=f"{uid}@x.com", display_name="Test",
        tier="free", is_archived=archived, notify_account_deletion=notify,
        last_active_at=datetime.now(UTC) - timedelta(days=days_inactive),
        referral_code=uid[:8].upper(), credits_balance=100,
    )


def _db_for_warning(users, log_exists=False) -> AsyncMock:
    db = AsyncMock()
    user_r = MagicMock(); user_r.all.return_value = users
    dedup_r = MagicMock()
    dedup_r.first.return_value = (
        DataRetentionLog(user_id="x", event_type="warning_sent", days_inactive=155)
        if log_exists else None
    )
    db.exec = AsyncMock(side_effect=[user_r, dedup_r])
    db.add = MagicMock(); db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_warning_sent_to_eligible_user(mocker):
    user = _free_user()
    db = _db_for_warning([user])
    email = AsyncMock(); email.send_account_deletion_warning = AsyncMock(return_value=True)
    mocker.patch("src.services.cold_data_service.settings", ADMIN_USER_IDS="")
    count = await ColdDataService(email_service=email).send_inactivity_warnings(db)
    assert count == 1
    email.send_account_deletion_warning.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_warning_skipped_for_admin(mocker):
    user = _free_user(uid="admin1")
    db = _db_for_warning([user])
    email = AsyncMock()
    mocker.patch("src.services.cold_data_service.settings", ADMIN_USER_IDS="admin1")
    count = await ColdDataService(email_service=email).send_inactivity_warnings(db)
    assert count == 0
    email.send_account_deletion_warning.assert_not_called()


@pytest.mark.asyncio
async def test_warning_deduplicated(mocker):
    user = _free_user()
    db = _db_for_warning([user], log_exists=True)
    email = AsyncMock()
    mocker.patch("src.services.cold_data_service.settings", ADMIN_USER_IDS="")
    count = await ColdDataService(email_service=email).send_inactivity_warnings(db)
    assert count == 0
    email.send_account_deletion_warning.assert_not_called()


def _db_for_purge(users, src_count=3) -> AsyncMock:
    db = AsyncMock()
    user_r = MagicMock(); user_r.all.return_value = users
    cnt_r = MagicMock(); cnt_r.one.return_value = src_count
    db.exec = AsyncMock(side_effect=[user_r, cnt_r])
    db.add = MagicMock(); db.commit = AsyncMock(); db.rollback = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_purge_archives_user_and_clears_credits(mocker):
    user = _free_user(uid="u2", days_inactive=185)
    db = _db_for_purge([user])
    deletion = MagicMock()
    for m in ("delete_storage_by_tenant", "delete_qdrant_by_tenant",
              "delete_neo4j_by_tenant", "delete_content_by_tenant"):
        setattr(deletion, m, AsyncMock())
    mocker.patch("src.services.cold_data_service.settings", ADMIN_USER_IDS="")
    count = await ColdDataService(deletion_service=deletion).purge_inactive_users(db)
    assert count == 1
    assert user.is_archived is True
    assert user.credits_balance == 0
    deletion.delete_content_by_tenant.assert_called_once_with(user.id, db)


@pytest.mark.asyncio
async def test_purge_skips_user_on_step_failure_no_is_archived(mocker):
    """AC-14: any step failure → rollback, skip user, is_archived stays False."""
    user = _free_user(uid="u3", days_inactive=185)
    db = _db_for_purge([user])
    deletion = MagicMock()
    deletion.delete_storage_by_tenant = AsyncMock(side_effect=Exception("S3 timeout"))
    mocker.patch("src.services.cold_data_service.settings", ADMIN_USER_IDS="")
    count = await ColdDataService(deletion_service=deletion).purge_inactive_users(db)
    assert count == 0
    assert user.is_archived is False
    db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_purge_skips_admin(mocker):
    user = _free_user(uid="admin2", days_inactive=200)
    db = _db_for_purge([user])
    deletion = MagicMock(); deletion.delete_storage_by_tenant = AsyncMock()
    mocker.patch("src.services.cold_data_service.settings", ADMIN_USER_IDS="admin2")
    count = await ColdDataService(deletion_service=deletion).purge_inactive_users(db)
    assert count == 0
    deletion.delete_storage_by_tenant.assert_not_called()
