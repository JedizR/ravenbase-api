# tests/unit/workers/test_cold_data_tasks.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workers.cold_data_tasks import cleanup_cold_data


@pytest.mark.asyncio
async def test_calls_both_phases():
    """Both warning and purge phases are called; result dict is correct."""
    svc = MagicMock()
    svc.send_inactivity_warnings = AsyncMock(return_value=3)
    svc.purge_inactive_users = AsyncMock(return_value=1)
    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    with patch("src.workers.cold_data_tasks.ColdDataService", return_value=svc):
        with patch("src.workers.cold_data_tasks.async_session_factory", return_value=db):
            result = await cleanup_cold_data({})

    assert result == {"warnings_sent": 3, "purges_executed": 1, "errors": 0}
    svc.send_inactivity_warnings.assert_called_once_with(db)
    svc.purge_inactive_users.assert_called_once_with(db)


@pytest.mark.asyncio
async def test_continues_if_warnings_phase_fails():
    """Warning phase failure increments errors; purge phase still runs."""
    svc = MagicMock()
    svc.send_inactivity_warnings = AsyncMock(side_effect=Exception("DB timeout"))
    svc.purge_inactive_users = AsyncMock(return_value=2)
    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)

    with patch("src.workers.cold_data_tasks.ColdDataService", return_value=svc):
        with patch("src.workers.cold_data_tasks.async_session_factory", return_value=db):
            result = await cleanup_cold_data({})

    svc.purge_inactive_users.assert_called_once()
    assert result["errors"] == 1
    assert result["purges_executed"] == 2
