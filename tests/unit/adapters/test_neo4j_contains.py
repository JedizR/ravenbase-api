# tests/unit/adapters/test_neo4j_contains.py
"""Tests for Neo4jAdapter.write_contains_edges()."""
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_write_contains_edges_merges_metadoc_node_and_edges():
    """write_contains_edges() creates the MetaDocument node and one CONTAINS edge per memory."""
    from src.adapters.neo4j_adapter import Neo4jAdapter

    adapter = Neo4jAdapter()
    adapter.run_query = AsyncMock(return_value=[])

    doc_id = "doc-uuid-001"
    memory_ids = ["mem-001", "mem-002"]
    tenant_id = "tenant-abc"

    await adapter.write_contains_edges(doc_id=doc_id, memory_ids=memory_ids, tenant_id=tenant_id)

    # One call to MERGE MetaDocument node, plus N calls for CONTAINS edges
    assert adapter.run_query.call_count == 3  # 1 node + 2 edges


@pytest.mark.asyncio
async def test_write_contains_edges_empty_memory_ids_only_merges_node():
    """write_contains_edges() with empty memory_ids still creates the MetaDocument node."""
    from src.adapters.neo4j_adapter import Neo4jAdapter

    adapter = Neo4jAdapter()
    adapter.run_query = AsyncMock(return_value=[])

    await adapter.write_contains_edges(
        doc_id="doc-001", memory_ids=[], tenant_id="tenant-abc"
    )

    # Only the node MERGE, no edge calls
    assert adapter.run_query.call_count == 1
