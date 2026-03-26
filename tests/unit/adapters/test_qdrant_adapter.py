# tests/unit/adapters/test_qdrant_adapter.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_client.models import FieldCondition, Filter, PointStruct


def test_init_does_not_open_connection() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    assert adapter._client is None


def test_tenant_filter_shape() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    f = adapter._tenant_filter("user-123")
    assert isinstance(f, Filter)
    assert len(f.must) == 1
    condition = f.must[0]
    assert isinstance(condition, FieldCondition)
    assert condition.key == "tenant_id"
    assert condition.match.value == "user-123"


@pytest.mark.asyncio
async def test_search_always_includes_tenant_filter() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    mock_client = AsyncMock()
    mock_result = MagicMock()
    mock_result.points = []
    mock_client.query_points = AsyncMock(return_value=mock_result)
    adapter._client = mock_client

    result = await adapter.search(query_vector=[0.1] * 1536, tenant_id="user-abc", limit=5)

    assert result == []
    mock_client.query_points.assert_called_once()
    kwargs = mock_client.query_points.call_args.kwargs
    assert kwargs["collection_name"] == "ravenbase_chunks"
    assert kwargs["limit"] == 5
    tenant_values = [c.match.value for c in kwargs["query_filter"].must]
    assert "user-abc" in tenant_values


@pytest.mark.asyncio
async def test_upsert_targets_correct_collection() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    mock_client = AsyncMock()
    mock_client.upsert = AsyncMock()
    adapter._client = mock_client

    points = [PointStruct(id="pt-1", vector=[0.1] * 1536, payload={"tenant_id": "t1"})]
    await adapter.upsert(points=points)

    mock_client.upsert.assert_called_once_with(
        collection_name="ravenbase_chunks", points=points
    )


@pytest.mark.asyncio
async def test_delete_by_filter_always_includes_tenant_filter() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    mock_client = AsyncMock()
    mock_client.delete = AsyncMock()
    adapter._client = mock_client

    await adapter.delete_by_filter(tenant_id="user-xyz")

    mock_client.delete.assert_called_once()
    kwargs = mock_client.delete.call_args.kwargs
    assert kwargs["collection_name"] == "ravenbase_chunks"
    tenant_values = [c.match.value for c in kwargs["points_selector"].filter.must]
    assert "user-xyz" in tenant_values


@pytest.mark.asyncio
async def test_count_includes_tenant_filter() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    mock_client = AsyncMock()
    mock_client.count = AsyncMock(return_value=MagicMock(count=42))
    adapter._client = mock_client

    result = await adapter.count(tenant_id="user-xyz")

    assert result == 42
    kwargs = mock_client.count.call_args.kwargs
    tenant_values = [c.match.value for c in kwargs["count_filter"].must]
    assert "user-xyz" in tenant_values


@pytest.mark.asyncio
async def test_verify_connectivity_returns_true_on_success() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    mock_client = AsyncMock()
    mock_client.get_collections = AsyncMock(return_value=MagicMock())
    adapter._client = mock_client

    assert await adapter.verify_connectivity() is True


@pytest.mark.asyncio
async def test_verify_connectivity_returns_false_on_error() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    mock_client = AsyncMock()
    mock_client.get_collections = AsyncMock(side_effect=Exception("unreachable"))
    adapter._client = mock_client

    assert await adapter.verify_connectivity() is False


def test_cleanup_clears_client() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    adapter._client = AsyncMock()
    adapter.cleanup()
    assert adapter._client is None
