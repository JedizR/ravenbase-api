# tests/integration/api/test_chat_endpoints.py
"""Integration tests for STORY-026 chat endpoints.

All external dependencies mocked. No live DB, Qdrant, Neo4j, or Anthropic.
Follows pattern from test_metadoc_endpoints.py.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.api.main import app
from src.models.chat_session import ChatSession
from src.models.user import User
from src.schemas.rag import RetrievedChunk

TEST_USER_ID = "user_test_" + str(uuid.uuid4()).replace("-", "")[:16]
TEST_OTHER_USER_ID = "user_other_" + str(uuid.uuid4()).replace("-", "")[:16]
TEST_SESSION_ID = uuid.uuid4()


def _make_user(credits: int = 50, tier: str = "free") -> User:
    return User(
        id=TEST_USER_ID,
        email="test@example.com",
        credits_balance=credits,
        tier=tier,
        preferred_model="claude-haiku-4-5-20251001",
    )


def _make_session(user_id: str = TEST_USER_ID, messages: list | None = None) -> ChatSession:
    return ChatSession(
        id=TEST_SESSION_ID,
        user_id=user_id,
        title="What ML projects have I done?",
        messages=messages or [],
    )


def _make_mock_db(user: User | None = None, session: ChatSession | None = None) -> AsyncMock:
    mock_db = AsyncMock()

    async def _get_side_effect(model_class, pk):
        if model_class is User:
            return user
        if model_class is ChatSession:
            return session
        return None

    mock_db.get = AsyncMock(side_effect=_get_side_effect)

    # get_sessions() calls db.exec() twice: once for COUNT, once for list.
    mock_count_result = MagicMock()
    mock_count_result.one = MagicMock(return_value=0)
    mock_count_result.one_or_none = MagicMock(return_value=None)
    mock_list_result = MagicMock()
    mock_list_result.all = MagicMock(return_value=[])
    mock_db.exec = AsyncMock(side_effect=[mock_count_result, mock_list_result])

    return mock_db


@pytest.fixture
async def chat_client():
    """Client with mocked auth + DB (user with sufficient credits)."""
    user = _make_user(credits=50)

    async def _override_db():
        yield _make_mock_db(user=user)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_USER_ID,
        "email": "test@example.com",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user, None)


@pytest.fixture
async def broke_client():
    """Client with 0 credits → 402 on send_message."""
    user = _make_user(credits=0)

    async def _override_db():
        yield _make_mock_db(user=user)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_USER_ID,
        "email": "test@example.com",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user, None)


# ── /v1/chat/message ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_message_unauthenticated_returns_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/chat/message", json={"message": "test"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_send_message_missing_body_returns_422(chat_client: AsyncClient) -> None:
    response = await chat_client.post("/v1/chat/message", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_send_message_insufficient_credits_returns_402(
    broke_client: AsyncClient,
) -> None:
    """User with 0 credits → 402 before any retrieval or LLM call (AC-9)."""
    response = await broke_client.post(
        "/v1/chat/message",
        json={"message": "What ML projects have I done?", "model": "haiku"},
    )
    assert response.status_code == 402
    assert response.json()["detail"]["code"] == "INSUFFICIENT_CREDITS"


@pytest.mark.asyncio
async def test_send_message_streams_sse_events(chat_client: AsyncClient) -> None:
    """Valid request → 200 with SSE events containing session, token, done (AC-1, AC-3, AC-11)."""
    fake_chunks = [
        RetrievedChunk(
            chunk_id="c1",
            content="I worked on a PyTorch image classifier.",
            source_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            memory_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            final_score=0.9,
            semantic_score=0.85,
            recency_weight=0.7,
        )
    ]

    async def fake_text_tokens():
        for chunk in ["Based on", " your notes", ", PyTorch."]:
            yield chunk

    mock_adapter = AsyncMock()
    mock_adapter.stream_completion = MagicMock(return_value=fake_text_tokens())

    with (
        patch("src.services.rag_service.RAGService") as mock_rag_cls,
        patch("src.adapters.anthropic_adapter.AnthropicAdapter", return_value=mock_adapter),
        patch("src.services.credit_service.CreditService.deduct", new_callable=AsyncMock),
    ):
        mock_rag_instance = AsyncMock()
        mock_rag_instance.retrieve = AsyncMock(return_value=fake_chunks)
        mock_rag_instance.cleanup = MagicMock()
        mock_rag_cls.return_value = mock_rag_instance

        response = await chat_client.post(
            "/v1/chat/message",
            json={"message": "What ML projects have I done?", "model": "haiku"},
        )

    assert response.status_code == 200
    body = response.text
    events = [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    types = [e["type"] for e in events]
    assert "session" in types, "First event must be session"
    assert "token" in types, "Token events must be present"
    assert "done" in types, "Final done event must be present"

    done_event = next(e for e in events if e["type"] == "done")
    assert "citations" in done_event
    assert "credits_consumed" in done_event
    assert done_event["credits_consumed"] == 3  # Haiku = 3 credits


# ── /v1/chat/sessions ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_returns_200(chat_client: AsyncClient) -> None:
    """GET /v1/chat/sessions returns paginated list (AC-4)."""
    response = await chat_client.get("/v1/chat/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "has_more" in data


@pytest.mark.asyncio
async def test_list_sessions_unauthenticated_returns_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/chat/sessions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_session_not_found_returns_404(chat_client: AsyncClient) -> None:
    """GET /v1/chat/sessions/{unknown_id} → 404 (AC-10: session not in user's scope)."""
    non_existent = uuid.uuid4()
    response = await chat_client.get(f"/v1/chat/sessions/{non_existent}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_session_not_found_returns_404(chat_client: AsyncClient) -> None:
    non_existent = uuid.uuid4()
    response = await chat_client.delete(f"/v1/chat/sessions/{non_existent}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_cannot_access_other_users_session() -> None:
    """User A cannot access User B's session — returns 404 not 403 (AC-10)."""
    other_session = _make_session(user_id=TEST_OTHER_USER_ID)
    user_a = _make_user(credits=50)

    async def _override_db():
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none = MagicMock(return_value=None)
        mock_db.exec = AsyncMock(return_value=mock_result)
        mock_db.get = AsyncMock(return_value=user_a)
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_USER_ID,
        "email": "test@example.com",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/v1/chat/sessions/{other_session.id}")

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user, None)

    assert response.status_code == 404
