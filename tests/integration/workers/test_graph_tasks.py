# tests/integration/workers/test_graph_tasks.py
"""Tests for the graph_extraction ARQ task function.

All external dependencies are mocked — this tests task wiring, not Neo4j/Qdrant.
"""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def arq_ctx() -> dict:
    return {}


@pytest.mark.asyncio
async def test_graph_extraction_returns_ok_on_success(arq_ctx) -> None:
    from src.workers.graph_tasks import graph_extraction  # noqa: PLC0415

    mock_stats = {"total_entities": 5, "total_memories": 3, "failed_chunks": 0}
    with patch("src.workers.graph_tasks.GraphService") as MockService:
        MockService.return_value.extract_and_write = AsyncMock(return_value=mock_stats)
        result = await graph_extraction(arq_ctx, source_id="src-1", tenant_id="t-1")

    assert result["status"] == "ok"
    assert result["total_entities"] == 5
    assert result["source_id"] == "src-1"
    MockService.return_value.extract_and_write.assert_called_once_with(
        source_id="src-1",
        tenant_id="t-1",
    )


@pytest.mark.asyncio
async def test_graph_extraction_returns_error_on_service_failure(arq_ctx) -> None:
    from src.workers.graph_tasks import graph_extraction  # noqa: PLC0415

    with patch("src.workers.graph_tasks.GraphService") as MockService:
        MockService.return_value.extract_and_write = AsyncMock(
            side_effect=RuntimeError("Neo4j unreachable")
        )
        result = await graph_extraction(arq_ctx, source_id="src-1", tenant_id="t-1")

    assert result["status"] == "error"
    assert "Neo4j unreachable" in result["error"]
    assert result["source_id"] == "src-1"


@pytest.mark.asyncio
async def test_graph_extraction_passes_tenant_id_to_service(arq_ctx) -> None:
    from src.workers.graph_tasks import graph_extraction  # noqa: PLC0415

    with patch("src.workers.graph_tasks.GraphService") as MockService:
        MockService.return_value.extract_and_write = AsyncMock(
            return_value={"total_entities": 0, "total_memories": 0, "failed_chunks": 0}
        )
        await graph_extraction(arq_ctx, source_id="src-99", tenant_id="user-ABC")

    MockService.return_value.extract_and_write.assert_called_once_with(
        source_id="src-99",
        tenant_id="user-ABC",
    )
