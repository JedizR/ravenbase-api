# tests/integration/api/test_metadoc_endpoints.py
"""Integration tests for POST /v1/metadoc/generate and GET /v1/metadoc/stream/{job_id}.

All external dependencies mocked. Tests run without live DB, Redis, or Anthropic.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.api.main import app
from src.models.user import User

TEST_TENANT_ID = str(uuid.uuid4())
TEST_USER_ID = uuid.UUID(TEST_TENANT_ID)


def _make_user(credits: int = 100, tier: str = "free") -> User:
    return User(
        id=TEST_USER_ID,
        email="test@example.com",
        credits_balance=credits,
        tier=tier,
        preferred_model="claude-haiku-4-5-20251001",
    )


def _make_mock_db(user: User | None) -> AsyncMock:
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=user)
    return mock_db


@pytest.fixture
async def metadoc_client(mocker):
    """Client with mocked auth, DB, and ARQ pool."""
    mock_job = MagicMock()
    mock_job.job_id = "test-metadoc-job-001"
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
    app.state.arq_pool = mock_pool

    user = _make_user(credits=100)

    async def _override_db():
        yield _make_mock_db(user)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    del app.state.arq_pool
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user, None)


@pytest.fixture
async def metadoc_client_broke(mocker):
    """Client where user has 0 credits → expects 402."""
    mock_pool = AsyncMock()
    app.state.arq_pool = mock_pool

    user = _make_user(credits=0)

    async def _override_db():
        yield _make_mock_db(user)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    del app.state.arq_pool
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user, None)


@pytest.mark.asyncio
async def test_generate_returns_202_with_job_id(metadoc_client: AsyncClient) -> None:
    """Valid request → 202 with job_id and estimated_credits."""
    response = await metadoc_client.post(
        "/v1/metadoc/generate",
        json={"prompt": "Tell me about Python"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["job_id"]
    assert data["estimated_credits"] == 18  # Haiku default


@pytest.mark.asyncio
async def test_generate_insufficient_credits_returns_402(
    metadoc_client_broke: AsyncClient,
) -> None:
    """User with 0 credits → 402 Payment Required, job NOT enqueued."""
    response = await metadoc_client_broke.post(
        "/v1/metadoc/generate",
        json={"prompt": "Tell me about my career"},
    )
    assert response.status_code == 402
    data = response.json()
    assert data["detail"]["code"] == "INSUFFICIENT_CREDITS"
    # ARQ pool should not have been called
    app.state.arq_pool.enqueue_job.assert_not_called()


@pytest.mark.asyncio
async def test_generate_missing_prompt_returns_422(metadoc_client: AsyncClient) -> None:
    """Missing required prompt field → 422 Unprocessable Entity."""
    response = await metadoc_client.post(
        "/v1/metadoc/generate",
        json={"profile_id": None},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_prompt_too_long_returns_422(metadoc_client: AsyncClient) -> None:
    """Prompt exceeding 2000 chars → 422."""
    long_prompt = "x" * 2001
    response = await metadoc_client.post(
        "/v1/metadoc/generate",
        json={"prompt": long_prompt},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_unauthenticated_returns_401() -> None:
    """Request without Authorization header → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/metadoc/generate", json={"prompt": "test"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stream_endpoint_requires_token_query_param() -> None:
    """GET /v1/metadoc/stream/{job_id} without ?token= → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/metadoc/stream/some-job-id")
    assert response.status_code == 401
