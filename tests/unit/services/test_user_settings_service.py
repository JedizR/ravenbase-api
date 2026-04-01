from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.models.user import User
from src.services.user_settings_service import UserSettingsService


@pytest.mark.asyncio
async def test_update_model_preference_rejects_invalid_model():
    mock_db = AsyncMock()
    svc = UserSettingsService()
    with pytest.raises(HTTPException) as exc:
        await svc.update_model_preference(mock_db, "user_001", "gpt-4")
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_update_model_preference_commits_valid_model():
    mock_db = AsyncMock()
    mock_user = MagicMock(spec=User)
    mock_user.preferred_model = "claude-haiku-4-5-20251001"
    mock_result = MagicMock()
    mock_result.one_or_none.return_value = mock_user
    mock_db.exec = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    svc = UserSettingsService()
    await svc.update_model_preference(mock_db, "user_001", "claude-sonnet-4-6")
    assert mock_user.preferred_model == "claude-sonnet-4-6"
    mock_db.commit.assert_awaited_once()
