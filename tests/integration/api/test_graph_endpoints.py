"""
Integration tests for GET /v1/graph/nodes and GET /v1/graph/neighborhood/{node_id}.

External dependencies (Neo4j, auth) are mocked — no live database required.
Run with: uv run pytest tests/integration/api/test_graph_endpoints.py -v
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import require_user
from src.api.main import app
from src.schemas.graph import GraphEdge, GraphNode, GraphResponse
from src.services.graph_service import GraphService


def test_schema_imports() -> None:
    """GraphNode, GraphEdge, GraphResponse are importable with correct fields."""
    node = GraphNode(
        id="abc",
        label="React",
        type="concept",
        properties={"name": "React"},
        memory_count=3,
    )
    assert node.id == "abc"
    assert node.memory_count == 3

    edge = GraphEdge(
        source="abc",
        target="def",
        type="RELATES_TO",
        properties={"weight": 0.8},
    )
    assert edge.source == "abc"

    resp = GraphResponse(nodes=[node], edges=[edge])
    assert len(resp.nodes) == 1
    assert len(resp.edges) == 1


TEST_TENANT_ID = "tenant-test-001"
TEST_NODE_ID = "node-test-001"

# ---------------------------------------------------------------------------
# GraphService unit tests (mocked Neo4jAdapter)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_nodes_for_explorer_returns_graph_response() -> None:
    """Service converts raw Neo4j rows into GraphResponse."""
    concept_id = str(uuid.uuid4())
    memory_id = str(uuid.uuid4())

    # Simulate two rows: Concept node with one EXTRACTED_FROM edge to a Memory
    raw_rows = [
        {
            "n_type": "Concept",
            "n_props": {"concept_id": concept_id, "name": "React", "tenant_id": TEST_TENANT_ID},
            "r_type": "EXTRACTED_FROM",
            "r_props": {},
            "m_type": "Memory",
            "m_props": {
                "memory_id": memory_id,
                "content": "User worked with React",
                "tenant_id": TEST_TENANT_ID,
            },
        },
    ]
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query = AsyncMock(return_value=raw_rows)

    svc = GraphService(neo4j_adapter=mock_neo4j)
    result = await svc.get_nodes_for_explorer(
        tenant_id=TEST_TENANT_ID,
        profile_id=None,
        node_types=None,
        limit=200,
    )

    assert isinstance(result, GraphResponse)
    node_ids = {n.id for n in result.nodes}
    assert concept_id in node_ids
    assert memory_id in node_ids
    edge_types = {e.type for e in result.edges}
    assert "EXTRACTED_FROM" in edge_types


@pytest.mark.asyncio
async def test_get_nodes_for_explorer_empty_returns_empty_response() -> None:
    """Empty Neo4j result → GraphResponse(nodes=[], edges=[]), NOT 404."""
    mock_neo4j = AsyncMock()
    mock_neo4j.run_query = AsyncMock(return_value=[])

    svc = GraphService(neo4j_adapter=mock_neo4j)
    result = await svc.get_nodes_for_explorer(
        tenant_id=TEST_TENANT_ID, profile_id=None, node_types=None, limit=200
    )

    assert result.nodes == []
    assert result.edges == []


@pytest.mark.asyncio
async def test_get_neighborhood_returns_graph_response() -> None:
    """Neighborhood service method combines two run_query calls into GraphResponse."""
    node_id_a = str(uuid.uuid4())
    node_id_b = str(uuid.uuid4())

    node_rows = [
        {
            "n_type": "Concept",
            "n_props": {"concept_id": node_id_a, "name": "React", "tenant_id": TEST_TENANT_ID},
        },
        {
            "n_type": "Concept",
            "n_props": {"concept_id": node_id_b, "name": "TypeScript", "tenant_id": TEST_TENANT_ID},
        },
    ]
    rel_rows = [
        {
            "r_type": "RELATES_TO",
            "r_props": {"weight": 0.9},
            "r_source_props": {"concept_id": node_id_a},
            "r_source_type": "Concept",
            "r_target_props": {"concept_id": node_id_b},
            "r_target_type": "Concept",
        }
    ]

    mock_neo4j = AsyncMock()
    mock_neo4j.run_query = AsyncMock(side_effect=[node_rows, rel_rows])

    svc = GraphService(neo4j_adapter=mock_neo4j)
    result = await svc.get_neighborhood(
        node_id=node_id_a, tenant_id=TEST_TENANT_ID, hops=2, limit=50
    )

    assert len(result.nodes) == 2
    assert len(result.edges) == 1
    assert result.edges[0].type == "RELATES_TO"
    assert result.edges[0].source == node_id_a
    assert result.edges[0].target == node_id_b


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def graph_client(mocker):
    """AsyncClient with mocked auth and GraphService. No live Neo4j required."""
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
        "tier": "free",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(require_user, None)


# ---------------------------------------------------------------------------
# GET /v1/graph/nodes tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_nodes_returns_200_with_graph_shape(graph_client: AsyncClient, mocker) -> None:
    """GET /v1/graph/nodes returns 200 with nodes + edges arrays."""
    mock_response = GraphResponse(
        nodes=[GraphNode(id="abc", label="React", type="Concept", properties={}, memory_count=2)],
        edges=[GraphEdge(source="abc", target="def", type="RELATES_TO", properties={})],
    )
    mocker.patch.object(
        GraphService, "get_nodes_for_explorer", new=AsyncMock(return_value=mock_response)
    )

    response = await graph_client.get("/v1/graph/nodes")

    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert data["nodes"][0]["id"] == "abc"
    assert data["nodes"][0]["label"] == "React"
    assert data["nodes"][0]["memory_count"] == 2
    assert data["edges"][0]["type"] == "RELATES_TO"


@pytest.mark.asyncio
async def test_get_nodes_empty_graph_returns_empty_arrays(
    graph_client: AsyncClient, mocker
) -> None:
    """Empty graph → 200 with {nodes: [], edges: []}, not 404."""
    mocker.patch.object(
        GraphService,
        "get_nodes_for_explorer",
        new=AsyncMock(return_value=GraphResponse(nodes=[], edges=[])),
    )

    response = await graph_client.get("/v1/graph/nodes")

    assert response.status_code == 200
    data = response.json()
    assert data == {"nodes": [], "edges": []}


@pytest.mark.asyncio
async def test_get_nodes_no_auth_returns_401() -> None:
    """Request without Authorization header → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/graph/nodes")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_nodes_passes_profile_id_to_service(graph_client: AsyncClient, mocker) -> None:
    """profile_id query param is forwarded to get_nodes_for_explorer()."""
    profile_id = str(uuid.uuid4())
    mock_fn = mocker.patch.object(
        GraphService,
        "get_nodes_for_explorer",
        new=AsyncMock(return_value=GraphResponse(nodes=[], edges=[])),
    )

    await graph_client.get(f"/v1/graph/nodes?profile_id={profile_id}")

    mock_fn.assert_called_once()
    call_kwargs = mock_fn.call_args.kwargs
    assert call_kwargs["profile_id"] == profile_id


@pytest.mark.asyncio
async def test_get_nodes_default_limit_is_200(graph_client: AsyncClient, mocker) -> None:
    """Default limit param is 200."""
    mock_fn = mocker.patch.object(
        GraphService,
        "get_nodes_for_explorer",
        new=AsyncMock(return_value=GraphResponse(nodes=[], edges=[])),
    )

    await graph_client.get("/v1/graph/nodes")

    call_kwargs = mock_fn.call_args.kwargs
    assert call_kwargs["limit"] == 200


# ---------------------------------------------------------------------------
# GET /v1/graph/neighborhood/{node_id} tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_neighborhood_returns_200(graph_client: AsyncClient, mocker) -> None:
    """GET /v1/graph/neighborhood/{node_id} returns 200 with nodes + edges."""
    mock_response = GraphResponse(
        nodes=[
            GraphNode(
                id=TEST_NODE_ID, label="React", type="Concept", properties={}, memory_count=0
            ),
            GraphNode(
                id="neighbor-1", label="TypeScript", type="Concept", properties={}, memory_count=0
            ),
        ],
        edges=[
            GraphEdge(source=TEST_NODE_ID, target="neighbor-1", type="RELATES_TO", properties={})
        ],
    )
    mocker.patch.object(GraphService, "get_neighborhood", new=AsyncMock(return_value=mock_response))

    response = await graph_client.get(f"/v1/graph/neighborhood/{TEST_NODE_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1


@pytest.mark.asyncio
async def test_get_neighborhood_default_hops_and_limit(graph_client: AsyncClient, mocker) -> None:
    """Default hops=2, default limit=50 are forwarded to get_neighborhood()."""
    mock_fn = mocker.patch.object(
        GraphService,
        "get_neighborhood",
        new=AsyncMock(return_value=GraphResponse(nodes=[], edges=[])),
    )

    await graph_client.get(f"/v1/graph/neighborhood/{TEST_NODE_ID}")

    call_kwargs = mock_fn.call_args.kwargs
    assert call_kwargs["hops"] == 2
    assert call_kwargs["limit"] == 50


@pytest.mark.asyncio
async def test_get_neighborhood_no_auth_returns_401() -> None:
    """Request without auth → 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/v1/graph/neighborhood/{TEST_NODE_ID}")
    assert response.status_code == 401
