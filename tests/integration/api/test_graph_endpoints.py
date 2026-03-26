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
