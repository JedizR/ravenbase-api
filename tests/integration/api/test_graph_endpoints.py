"""
Integration tests for GET /v1/graph/nodes and GET /v1/graph/neighborhood/{node_id}.

External dependencies (Neo4j, auth) are mocked — no live database required.
Run with: uv run pytest tests/integration/api/test_graph_endpoints.py -v
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient  # noqa: F401

from src.api.dependencies.auth import require_user  # noqa: F401
from src.api.main import app  # noqa: F401
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
