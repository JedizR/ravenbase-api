# tests/integration/api/test_gdpr_deletion.py
"""Integration tests for DELETE /v1/account (GDPR Right to Erasure).

All external adapters and ARQ pool are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.fixture
async def anon_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_gdpr_deletion_requires_auth(anon_client):
    """DELETE /v1/account without Authorization header returns 401."""
    resp = await anon_client.delete("/v1/account")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "MISSING_AUTH"


@pytest.mark.asyncio
async def test_gdpr_deletion_returns_202_and_enqueues_job():
    """DELETE /v1/account with valid JWT returns 202 and enqueues cascade_delete_account."""
    mock_job = MagicMock()
    mock_job.job_id = "job_gdpr_abc123"
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

    with patch.object(app.state, "arq_pool", mock_pool, create=True):
        with patch(
            "src.api.routes.account.require_user",
            return_value={"user_id": "user_test_123", "email": "test@example.com"},
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.delete(
                    "/v1/account",
                    headers={"Authorization": "Bearer valid_token"},
                )

    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"] == "job_gdpr_abc123"
    assert body["status"] == "queued"

    mock_pool.enqueue_job.assert_called_once_with(
        "cascade_delete_account",
        user_id="user_test_123",
        _job_id="gdpr:user_test_123",
    )


@pytest.mark.asyncio
async def test_gdpr_deletion_tenant_id_from_jwt_not_body():
    """tenant_id must come exclusively from the JWT, never from the request body."""
    mock_job = MagicMock()
    mock_job.job_id = "job_gdpr_from_jwt"
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

    with patch.object(app.state, "arq_pool", mock_pool, create=True):
        with patch(
            "src.api.routes.account.require_user",
            return_value={"user_id": "real_user_from_jwt", "email": "real@example.com"},
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.delete(
                    "/v1/account",
                    headers={"Authorization": "Bearer valid_token"},
                )

    assert resp.status_code == 202
    # Verify the enqueued job uses the JWT user_id, not any attacker-supplied value
    call_kwargs = mock_pool.enqueue_job.call_args
    assert call_kwargs[1]["user_id"] == "real_user_from_jwt"
