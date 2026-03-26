# tests/integration/api/test_ingest_stream.py
"""Integration tests for GET /v1/ingest/stream/{source_id} SSE endpoint.

Redis pub/sub is fully mocked — no live Redis required.
Run with: uv run pytest tests/integration/api/test_ingest_stream.py -v
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import verify_token_query_param
from src.api.main import app

TEST_TENANT_ID = str(uuid.uuid4())
TEST_SOURCE_ID = str(uuid.uuid4())

PROCESSING_MSG = json.dumps(
    {"progress_pct": 50, "message": "Parsing document...", "status": "processing"}
).encode()
COMPLETED_MSG = json.dumps(
    {"progress_pct": 100, "message": "Ingestion complete!", "status": "completed"}
).encode()
FAILED_MSG = json.dumps(
    {"progress_pct": 0, "message": "Ingestion failed", "status": "failed"}
).encode()


def _make_mock_redis(messages: list[dict]):
    """Build a mock redis connection whose pubsub.listen() yields `messages`."""

    async def _listen():
        for msg in messages:
            yield msg

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.listen = MagicMock(return_value=_listen())

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mock_redis.aclose = AsyncMock()

    return mock_redis, mock_pubsub


@pytest.fixture(autouse=True)
def _override_auth():
    """Skip real JWT validation for all tests in this module."""
    app.dependency_overrides[verify_token_query_param] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
        "tier": "free",
    }
    yield
    app.dependency_overrides.pop(verify_token_query_param, None)


@pytest.mark.asyncio
async def test_stream_returns_event_stream_content_type(mocker):
    """GET /stream/{source_id} → Content-Type: text/event-stream."""
    mock_redis, _ = _make_mock_redis(
        [
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": COMPLETED_MSG},
        ]
    )
    mocker.patch("src.api.routes.ingest.aioredis.from_url", new=AsyncMock(return_value=mock_redis))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("GET", f"/v1/ingest/stream/{TEST_SOURCE_ID}?token=fake") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_stream_emits_progress_events(mocker):
    """Stream emits data: lines for each message-type Redis event."""
    mock_redis, _ = _make_mock_redis(
        [
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": PROCESSING_MSG},
            {"type": "message", "data": COMPLETED_MSG},
        ]
    )
    mocker.patch("src.api.routes.ingest.aioredis.from_url", new=AsyncMock(return_value=mock_redis))

    body = ""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("GET", f"/v1/ingest/stream/{TEST_SOURCE_ID}?token=fake") as response:
            async for chunk in response.aiter_text():
                body += chunk

    assert '"progress_pct": 50' in body
    assert '"status": "processing"' in body
    assert '"progress_pct": 100' in body
    assert '"status": "completed"' in body


@pytest.mark.asyncio
async def test_stream_closes_on_completed(mocker):
    """Stream closes (does not hang) when status=completed is received."""
    mock_redis, mock_pubsub = _make_mock_redis(
        [
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": PROCESSING_MSG},
            {"type": "message", "data": COMPLETED_MSG},
            # This message must NOT appear in the body — stream already closed
            {
                "type": "message",
                "data": b'{"progress_pct": 0, "message": "ghost", "status": "processing"}',
            },
        ]
    )
    mocker.patch("src.api.routes.ingest.aioredis.from_url", new=AsyncMock(return_value=mock_redis))

    body = ""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("GET", f"/v1/ingest/stream/{TEST_SOURCE_ID}?token=fake") as response:
            async for chunk in response.aiter_text():
                body += chunk

    assert "ghost" not in body


@pytest.mark.asyncio
async def test_stream_closes_on_failed(mocker):
    """Stream closes when status=failed is received."""
    mock_redis, _ = _make_mock_redis(
        [
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": FAILED_MSG},
        ]
    )
    mocker.patch("src.api.routes.ingest.aioredis.from_url", new=AsyncMock(return_value=mock_redis))

    body = ""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("GET", f"/v1/ingest/stream/{TEST_SOURCE_ID}?token=fake") as response:
            async for chunk in response.aiter_text():
                body += chunk

    assert '"status": "failed"' in body


@pytest.mark.asyncio
async def test_stream_always_unsubscribes_on_disconnect(mocker):
    """Redis pubsub.unsubscribe is called even when generator is interrupted."""

    # Simulate a real-world scenario: Redis raises ConnectionError mid-stream
    async def _listen_raising():
        yield {"type": "subscribe", "data": 1}
        yield {"type": "message", "data": PROCESSING_MSG}
        raise Exception("simulated disconnect")  # real exception, not GeneratorExit

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.listen = MagicMock(return_value=_listen_raising())

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mock_redis.aclose = AsyncMock()

    mocker.patch("src.api.routes.ingest.aioredis.from_url", new=AsyncMock(return_value=mock_redis))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        try:
            async with ac.stream(
                "GET", f"/v1/ingest/stream/{TEST_SOURCE_ID}?token=fake"
            ) as response:
                async for _ in response.aiter_text():
                    pass
        except Exception:
            pass

    # unsubscribe must have been called (try/finally guarantee)
    mock_pubsub.unsubscribe.assert_called_once()
    mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_stream_missing_token_returns_422():
    """Missing ?token= → 422 Unprocessable Entity (FastAPI Query validation)."""
    app.dependency_overrides.pop(verify_token_query_param, None)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/v1/ingest/stream/{TEST_SOURCE_ID}")
        assert response.status_code == 422
    finally:
        app.dependency_overrides[verify_token_query_param] = lambda: {
            "user_id": TEST_TENANT_ID,
            "email": "test@example.com",
            "tier": "free",
        }
