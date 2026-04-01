import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.models.profile import SystemProfile
from src.services.profile_service import ProfileService


@pytest.mark.asyncio
async def test_list_profiles_returns_all_user_profiles():
    mock_db = AsyncMock()
    profile = MagicMock(spec=SystemProfile)
    profile.user_id = "user_001"
    mock_result = MagicMock()
    mock_result.all.return_value = [profile]
    mock_db.exec = AsyncMock(return_value=mock_result)

    svc = ProfileService()
    result = await svc.list_profiles(mock_db, "user_001")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_delete_profile_raises_if_last_profile():
    profile_id = uuid.uuid4()
    mock_db = AsyncMock()
    profile = MagicMock(spec=SystemProfile)
    profile.id = profile_id
    profile.user_id = "user_001"

    # first exec: find target profile
    # second exec: count all profiles (returns 1 — the last one)
    call_count = 0

    async def side_effect(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.one_or_none.return_value = profile
        else:
            result.all.return_value = [profile]
        return result

    mock_db.exec = AsyncMock(side_effect=side_effect)

    svc = ProfileService()
    with pytest.raises(HTTPException) as exc:
        await svc.delete_profile(mock_db, profile_id, "user_001")
    assert exc.value.status_code == 400
    assert "CANNOT_DELETE_LAST_PROFILE" in str(exc.value.detail)
