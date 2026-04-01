from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.user import User
from src.services.user_service import UserService


@pytest.mark.asyncio
async def test_update_user_tier_commits_new_tier():
    mock_db = AsyncMock()
    mock_user = MagicMock(spec=User)
    mock_user.tier = "free"
    mock_result = MagicMock()
    mock_result.first.return_value = mock_user
    mock_db.exec = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    svc = UserService()
    await svc.update_user_tier(mock_db, "user_001", "pro")
    assert mock_user.tier == "pro"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revert_subscription_to_free_when_customer_found():
    mock_db = AsyncMock()
    mock_user = MagicMock(spec=User)
    mock_user.tier = "pro"
    mock_result = MagicMock()
    mock_result.first.return_value = mock_user
    mock_db.exec = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    svc = UserService()
    await svc.revert_subscription_to_free(mock_db, "cus_test_001")
    assert mock_user.tier == "free"
    mock_db.commit.assert_awaited_once()
