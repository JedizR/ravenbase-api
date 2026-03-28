# tests/integration/api/test_graph_query.py
"""Integration tests for POST /v1/graph/query (STORY-029).

External dependencies (Neo4j, LLM, DB) are fully mocked.
Run with: uv run pytest tests/integration/api/test_graph_query.py -v
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.api.main import app
from src.schemas.graph import GraphNode, GraphQueryResponse, GraphResponse
from src.services.graph_query_service import GraphQueryService

TEST_TENANT_ID = "tenant-029-" + str(uuid.uuid4())[:8]


def _make_mock_db(credits: int = 100) -> AsyncMock:
    """Mock AsyncSession that returns a User with the given credit balance."""
    from src.models.user import User  # noqa: PLC0415
    user = User(
        id=TEST_TENANT_ID,
        email="test@example.com",
        credits_balance=credits,
        tier="free",
        preferred_model="claude-haiku-4-5-20251001",
    )
    mock_result = MagicMock()
    mock_result.one.return_value = user
    db = AsyncMock()
    db.exec = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


def _make_service_response(node_count: int = 1) -> GraphQueryResponse:
    nodes = [
        GraphNode(id=f"mem-{i:03d}", label=f"Memory {i}", type="Memory", properties={})
        for i in range(node_count)
    ]
    explanation = (
        f"Found {node_count} node{'s' if node_count != 1 else ''} matching your query."
        if node_count else "No memories found matching your query."
    )
    return GraphQueryResponse(
        cypher="MATCH (n:Memory) WHERE n.tenant_id = $tenant_id RETURN n LIMIT 20",
        results=GraphResponse(nodes=nodes, edges=[]),
        explanation=explanation,
        query_time_ms=42,
    )


@pytest.fixture
def _auth_overrides():
    """Apply auth dependency override; clean up after test."""
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
    }
    yield
    app.dependency_overrides.pop(require_user, None)
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Schema-level tests (no HTTP, fast)
# ---------------------------------------------------------------------------

def test_graph_query_request_defaults() -> None:
    from src.schemas.graph import GraphQueryRequest  # noqa: PLC0415
    req = GraphQueryRequest(query="Show my Python projects", limit=10)
    assert req.limit == 10
    assert req.profile_id is None

def test_graph_query_request_limit_cap_enforced_by_schema() -> None:
    from pydantic import ValidationError  # noqa: PLC0415

    from src.schemas.graph import GraphQueryRequest  # noqa: PLC0415
    with pytest.raises(ValidationError):
        GraphQueryRequest(query="test", limit=51)

# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_graph_query_returns_200_correct_shape(_auth_overrides, mocker) -> None:
    """AC-1: returns cypher, results.nodes, results.edges, explanation, query_time_ms."""
    async def _async_gen():
        yield _make_mock_db(100)

    app.dependency_overrides[get_db] = _async_gen

    mocker.patch.object(GraphQueryService, "execute_nl_query", new=AsyncMock(return_value=_make_service_response(2)))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/v1/graph/query",
            json={"query": "Show my Python projects", "limit": 10},
            headers={"Authorization": "Bearer fake"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "cypher" in data
    assert "results" in data
    assert "nodes" in data["results"]
    assert "edges" in data["results"]
    assert "explanation" in data
    assert "query_time_ms" in data
    assert len(data["results"]["nodes"]) == 2

@pytest.mark.asyncio
async def test_post_graph_query_no_auth_returns_401() -> None:
    """No Authorization header → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/graph/query", json={"query": "test"})
    assert resp.status_code == 401

# ---------------------------------------------------------------------------
# AC-3: Unsafe Cypher → 422 UNSAFE_QUERY
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_graph_query_unsafe_cypher_returns_422(_auth_overrides, mocker) -> None:
    from fastapi import HTTPException  # noqa: PLC0415

    from src.core.errors import ErrorCode  # noqa: PLC0415

    async def _async_gen():
        yield _make_mock_db(100)
    app.dependency_overrides[get_db] = _async_gen

    mocker.patch.object(
        GraphQueryService, "execute_nl_query",
        side_effect=HTTPException(
            status_code=422,
            detail={"code": ErrorCode.UNSAFE_QUERY, "message": "Query must be read-only"},
        ),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/v1/graph/query",
            json={"query": "Delete all my memories"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "UNSAFE_QUERY"

# ---------------------------------------------------------------------------
# AC-8: Credit check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_graph_query_insufficient_credits_returns_402(_auth_overrides, mocker) -> None:
    """0-credit user → 402 before service is called."""
    async def _async_gen():
        yield _make_mock_db(credits=0)
    app.dependency_overrides[get_db] = _async_gen

    mock_execute = mocker.patch.object(
        GraphQueryService, "execute_nl_query", new=AsyncMock(return_value=_make_service_response())
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/v1/graph/query",
            json={"query": "test"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 402
    assert resp.json()["detail"]["code"] == "INSUFFICIENT_CREDITS"
    mock_execute.assert_not_called()

# ---------------------------------------------------------------------------
# AC-9: Empty results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_graph_query_empty_results_returns_200(_auth_overrides, mocker) -> None:
    async def _async_gen():
        yield _make_mock_db(100)
    app.dependency_overrides[get_db] = _async_gen

    empty = GraphQueryResponse(
        cypher="MATCH (n:Memory) WHERE n.tenant_id = $tenant_id RETURN n LIMIT 20",
        results=GraphResponse(nodes=[], edges=[]),
        explanation="No memories found matching your query.",
        query_time_ms=5,
    )
    mocker.patch.object(GraphQueryService, "execute_nl_query", new=AsyncMock(return_value=empty))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/v1/graph/query",
            json={"query": "Projects from 1900"},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"]["nodes"] == []
    assert data["explanation"] == "No memories found matching your query."

# ---------------------------------------------------------------------------
# AC-10: limit schema cap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_graph_query_limit_51_rejected_by_schema(_auth_overrides) -> None:
    async def _async_gen():
        yield _make_mock_db(100)
    app.dependency_overrides[get_db] = _async_gen

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/v1/graph/query",
            json={"query": "test", "limit": 51},
            headers={"Authorization": "Bearer fake"},
        )
    assert resp.status_code == 422  # Pydantic validation error

# ---------------------------------------------------------------------------
# profile_id forwarding
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_graph_query_profile_id_forwarded(_auth_overrides, mocker) -> None:
    async def _async_gen():
        yield _make_mock_db(100)
    app.dependency_overrides[get_db] = _async_gen

    profile_id = str(uuid.uuid4())
    captured: dict = {}

    async def _capture(**kwargs):
        captured.update(kwargs)
        return _make_service_response(0)

    mocker.patch.object(GraphQueryService, "execute_nl_query", side_effect=_capture)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(
            "/v1/graph/query",
            json={"query": "test", "profile_id": profile_id},
            headers={"Authorization": "Bearer fake"},
        )
    assert captured.get("profile_id") == profile_id
