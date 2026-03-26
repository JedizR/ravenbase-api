# tests/integration/api/test_ingest_text.py
"""
Integration tests for POST /v1/ingest/text.

All external dependencies (DB, ARQ) are mocked so this suite runs
without a live database or network.

Run with: uv run pytest tests/integration/api/test_ingest_text.py -v
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.api.main import app
from src.core.errors import ErrorCode

TEST_TENANT_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _make_mock_db(existing_source=None):  # type: ignore[type-arg]
    """Build a mock AsyncSession with no pre-existing Source (no dedup)."""
    mock_result = MagicMock()
    mock_result.first.return_value = existing_source
    mock_db = AsyncMock()
    mock_db.exec = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    return mock_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def text_ingest_client():
    """Client with mocked ARQ pool, auth, and DB (no duplicates)."""
    mock_job = MagicMock()
    mock_job.job_id = "test-job-text-abc123"
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
    app.state.arq_pool = mock_pool

    mock_db = _make_mock_db(existing_source=None)

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
        "tier": "free",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    del app.state.arq_pool
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user, None)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_text_happy_path_returns_202(text_ingest_client: AsyncClient) -> None:
    """Valid text body → 202, status=queued, duplicate=False, valid UUID source_id."""
    response = await text_ingest_client.post(
        "/v1/ingest/text",
        json={"content": "Hello, world! This is a quick capture.", "tags": ["test"]},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["duplicate"] is False
    assert data["job_id"] == "test-job-text-abc123"
    assert uuid.UUID(data["source_id"])  # valid UUID, no exception raised


@pytest.mark.asyncio
async def test_ingest_text_too_long_returns_422(text_ingest_client: AsyncClient) -> None:
    """Text with 50,001 characters → 422 TEXT_TOO_LONG."""
    long_content = "x" * 50_001

    response = await text_ingest_client.post(
        "/v1/ingest/text",
        json={"content": long_content, "tags": []},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == ErrorCode.TEXT_TOO_LONG
