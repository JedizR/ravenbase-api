# tests/integration/api/test_conflict_api.py
"""
Integration tests for GET /v1/conflicts, POST /v1/conflicts/{id}/resolve,
and POST /v1/conflicts/{id}/undo.

All external dependencies (DB, Neo4j, LLMRouter, auth) are mocked so this
suite runs without a live database or network.

Run with: uv run pytest tests/integration/api/test_conflict_api.py -v
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.api.main import app
from src.models.conflict import Conflict, ConflictStatus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_USER_ID = str(uuid.uuid4())
OTHER_USER_ID = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conflict(
    user_id: str = TEST_USER_ID,
    status: str = ConflictStatus.PENDING,
    resolved_at: datetime | None = None,
) -> Conflict:
    c = Conflict(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        incumbent_memory_id="mem-incumbent-1",
        challenger_memory_id="mem-challenger-1",
        incumbent_content="I work at Acme Corp.",
        challenger_content="I work at Globex Corp.",
        ai_classification="CONTRADICTION",
        confidence_score=0.92,
        status=status,
        resolved_at=resolved_at,
        created_at=datetime.now(UTC),
    )
    return c


def _make_mock_db(conflict: Conflict | None = None, total: int = 0) -> AsyncMock:
    """Build a mock AsyncSession for list/get operations."""
    mock_result_exec = MagicMock()
    mock_result_exec.all.return_value = [conflict] if conflict else []
    mock_result_exec.one.return_value = total

    mock_db = AsyncMock()
    mock_db.exec = AsyncMock(return_value=mock_result_exec)
    mock_db.get = AsyncMock(return_value=conflict)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    return mock_db


async def _mock_db_gen(mock_db: AsyncMock):
    yield mock_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authed_client():
    """Returns an async client factory that overrides auth and DB."""

    async def _make(mock_db: AsyncMock, user_id: str = TEST_USER_ID):
        app.dependency_overrides[require_user] = lambda: {
            "user_id": user_id,
            "email": "test@example.com",
        }

        # FastAPI resolves generator overrides by iterating them — define a named
        # async generator function (not a lambda returning a generator) so that
        # FastAPI recognises it as a yield-based dependency.
        async def _db_override():
            yield mock_db

        app.dependency_overrides[get_db] = _db_override
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    return _make


# ---------------------------------------------------------------------------
# GET /v1/conflicts
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_conflicts_empty(authed_client):
    mock_db = _make_mock_db(conflict=None, total=0)
    async with await authed_client(mock_db) as client:
        resp = await client.get("/v1/conflicts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["has_more"] is False
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_list_conflicts_with_results(authed_client):
    conflict = _make_conflict()
    # Return total=1 on count query, [conflict] on rows query
    mock_result_count = MagicMock()
    mock_result_count.one.return_value = 1
    mock_result_rows = MagicMock()
    mock_result_rows.all.return_value = [conflict]

    mock_db = AsyncMock()
    call_count = [0]

    async def exec_side_effect(stmt):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_result_count
        return mock_result_rows

    mock_db.exec = AsyncMock(side_effect=exec_side_effect)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    async with await authed_client(mock_db) as client:
        resp = await client.get("/v1/conflicts?status=pending")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == "pending"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /v1/conflicts/{id}/resolve
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_resolve_conflict_not_found(authed_client):
    mock_db = _make_mock_db(conflict=None)
    async with await authed_client(mock_db) as client:
        resp = await client.post(
            f"/v1/conflicts/{uuid.uuid4()}/resolve",
            json={"action": "KEEP_OLD"},
        )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "CONFLICT_NOT_FOUND"
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_resolve_wrong_user(authed_client):
    conflict = _make_conflict(user_id=OTHER_USER_ID)
    mock_db = _make_mock_db(conflict=conflict)
    async with await authed_client(mock_db) as client:
        resp = await client.post(
            f"/v1/conflicts/{conflict.id}/resolve",
            json={"action": "KEEP_OLD"},
        )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "CONFLICT_FORBIDDEN"
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_resolve_already_resolved(authed_client):
    conflict = _make_conflict(status=ConflictStatus.RESOLVED_KEEP_OLD)
    mock_db = _make_mock_db(conflict=conflict)
    async with await authed_client(mock_db) as client:
        resp = await client.post(
            f"/v1/conflicts/{conflict.id}/resolve",
            json={"action": "KEEP_OLD"},
        )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CONFLICT_ALREADY_RESOLVED"
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_resolve_keep_old(authed_client):
    conflict = _make_conflict()
    mock_db = _make_mock_db(conflict=conflict)
    async with await authed_client(mock_db) as client:
        resp = await client.post(
            f"/v1/conflicts/{conflict.id}/resolve",
            json={"action": "KEEP_OLD"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == ConflictStatus.RESOLVED_KEEP_OLD
    assert body["graph_mutations"]["superseded_memory_id"] is None
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_resolve_accept_new(authed_client):
    conflict = _make_conflict()
    mock_db = _make_mock_db(conflict=conflict)
    with patch(
        "src.adapters.neo4j_adapter.Neo4jAdapter.run_query",
        new=AsyncMock(return_value=[]),
    ):
        async with await authed_client(mock_db) as client:
            resp = await client.post(
                f"/v1/conflicts/{conflict.id}/resolve",
                json={"action": "ACCEPT_NEW"},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == ConflictStatus.RESOLVED_ACCEPT_NEW
    assert body["graph_mutations"]["superseded_memory_id"] == "mem-incumbent-1"
    assert body["graph_mutations"]["active_memory_id"] == "mem-challenger-1"
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_resolve_custom_missing_text(authed_client):
    conflict = _make_conflict()
    mock_db = _make_mock_db(conflict=conflict)
    async with await authed_client(mock_db) as client:
        resp = await client.post(
            f"/v1/conflicts/{conflict.id}/resolve",
            json={"action": "CUSTOM"},
        )
    # Pydantic model_validator raises ValueError → 422
    assert resp.status_code == 422
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_resolve_custom_with_text(authed_client):
    conflict = _make_conflict()
    mock_db = _make_mock_db(conflict=conflict)
    llm_payload = (
        '{"active_memory_id": "mem-challenger-1", '
        '"superseded_memory_id": "mem-incumbent-1", '
        '"new_tags": ["updated"]}'
    )
    with (
        patch(
            "src.adapters.llm_router.LLMRouter.complete",
            new=AsyncMock(return_value=llm_payload),
        ),
        patch(
            "src.adapters.neo4j_adapter.Neo4jAdapter.write_relationships",
            new=AsyncMock(),
        ),
    ):
        async with await authed_client(mock_db) as client:
            resp = await client.post(
                f"/v1/conflicts/{conflict.id}/resolve",
                json={"action": "CUSTOM", "custom_text": "Keep the newer entry."},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == ConflictStatus.RESOLVED_CUSTOM
    assert body["graph_mutations"]["new_tags"] == ["updated"]
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /v1/conflicts/{id}/undo
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_undo_conflict_not_found(authed_client):
    mock_db = _make_mock_db(conflict=None)
    async with await authed_client(mock_db) as client:
        resp = await client.post(f"/v1/conflicts/{uuid.uuid4()}/undo")
    assert resp.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_undo_wrong_user(authed_client):
    conflict = _make_conflict(
        user_id=OTHER_USER_ID,
        status=ConflictStatus.RESOLVED_KEEP_OLD,
        resolved_at=datetime.now(UTC),
    )
    mock_db = _make_mock_db(conflict=conflict)
    async with await authed_client(mock_db) as client:
        resp = await client.post(f"/v1/conflicts/{conflict.id}/undo")
    assert resp.status_code == 403
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_undo_not_resolved(authed_client):
    conflict = _make_conflict(status=ConflictStatus.PENDING)
    mock_db = _make_mock_db(conflict=conflict)
    async with await authed_client(mock_db) as client:
        resp = await client.post(f"/v1/conflicts/{conflict.id}/undo")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "CONFLICT_NOT_RESOLVED"
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_undo_window_expired(authed_client):
    resolved_at = datetime.now(UTC) - timedelta(seconds=31)
    conflict = _make_conflict(
        status=ConflictStatus.RESOLVED_KEEP_OLD,
        resolved_at=resolved_at,
    )
    mock_db = _make_mock_db(conflict=conflict)
    async with await authed_client(mock_db) as client:
        resp = await client.post(f"/v1/conflicts/{conflict.id}/undo")
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "UNDO_WINDOW_EXPIRED"
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_undo_within_window_keep_old(authed_client):
    resolved_at = datetime.now(UTC) - timedelta(seconds=5)
    conflict = _make_conflict(
        status=ConflictStatus.RESOLVED_KEEP_OLD,
        resolved_at=resolved_at,
    )
    mock_db = _make_mock_db(conflict=conflict)
    async with await authed_client(mock_db) as client:
        resp = await client.post(f"/v1/conflicts/{conflict.id}/undo")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert "undone" in body["message"].lower()
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_undo_within_window_accept_new(authed_client):
    resolved_at = datetime.now(UTC) - timedelta(seconds=5)
    conflict = _make_conflict(
        status=ConflictStatus.RESOLVED_ACCEPT_NEW,
        resolved_at=resolved_at,
    )
    mock_db = _make_mock_db(conflict=conflict)
    with patch(
        "src.adapters.neo4j_adapter.Neo4jAdapter.run_query",
        new=AsyncMock(return_value=[]),
    ):
        async with await authed_client(mock_db) as client:
            resp = await client.post(f"/v1/conflicts/{conflict.id}/undo")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    app.dependency_overrides.clear()
