# tests/unit/api/test_activity_middleware.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from src.api.middleware.activity import ActivityTrackingMiddleware, _update_last_active


@pytest.mark.asyncio
async def test_update_last_active_writes_to_db_and_sets_redis():
    """Happy path: DB updated, Redis key set with 24h TTL."""
    mock_redis = AsyncMock()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_db)

    await _update_last_active(mock_redis, mock_factory, "user_abc")

    mock_db.execute.assert_called_once()
    sql_call = str(mock_db.execute.call_args[0][0])
    assert "users" in sql_call
    assert mock_db.execute.call_args[0][1]["uid"] == "user_abc"
    mock_db.commit.assert_called_once()
    mock_redis.set.assert_called_once()
    call_kwargs = mock_redis.set.call_args
    assert "activity:user_abc" in str(call_kwargs)


@pytest.mark.asyncio
async def test_update_last_active_does_not_set_redis_on_db_failure():
    """DB failure: Redis key must NOT be set (so next request retries)."""
    mock_redis = AsyncMock()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("DB down"))
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_db)

    # Must not raise
    await _update_last_active(mock_redis, mock_factory, "user_abc")
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_skips_when_no_user_id():
    """Unauthenticated requests (no request.state.user_id) are silently skipped."""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=False)

    async def homepage(request: Request):
        return JSONResponse({"ok": True})

    inner = Starlette(routes=[Route("/", homepage)])
    inner.state.redis = mock_redis
    app = ActivityTrackingMiddleware(inner)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/")

    assert resp.status_code == 200
    mock_redis.exists.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_skips_skip_paths():
    """Health-check and webhook paths are never tracked."""
    mock_redis = AsyncMock()

    async def health(request: Request):
        request.state.user_id = "user_xyz"  # even if set, path is skipped
        return JSONResponse({"ok": True})

    inner = Starlette(routes=[Route("/health", health)])
    inner.state.redis = mock_redis
    app = ActivityTrackingMiddleware(inner)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")

    assert resp.status_code == 200
    mock_redis.exists.assert_not_called()
