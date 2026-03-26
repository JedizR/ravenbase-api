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

    mock_client.upsert.assert_called_once_with(collection_name="ravenbase_chunks", points=points)


@pytest.mark.asyncio
async def test_upsert_raises_if_point_missing_tenant_id() -> None:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    mock_client = AsyncMock()
    adapter._client = mock_client

    points_without_tenant = [PointStruct(id="pt-1", vector=[0.1] * 1536, payload={"other": "data"})]
    with pytest.raises(ValueError, match="tenant_id"):
        await adapter.upsert(points=points_without_tenant)

    mock_client.upsert.assert_not_called()


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


@pytest.mark.asyncio
async def test_scroll_by_source_enforces_tenant_and_source_filter() -> None:
    from unittest.mock import AsyncMock, MagicMock  # noqa: PLC0415

    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()
    mock_record = MagicMock()
    mock_record.payload = {"tenant_id": "t1", "source_id": "s1", "text": "hello"}
    mock_client = AsyncMock()
    mock_client.scroll = AsyncMock(return_value=([mock_record], None))
    adapter._client = mock_client

    results = await adapter.scroll_by_source("s1", "t1")

    assert len(results) == 1
    assert results[0]["text"] == "hello"
    call_kwargs = mock_client.scroll.call_args.kwargs
    must_conditions = call_kwargs["scroll_filter"].must
    keys = [c.key for c in must_conditions]
    assert "tenant_id" in keys
    assert "source_id" in keys


@pytest.mark.asyncio
async def test_scroll_by_source_paginates_all_results() -> None:
    from unittest.mock import AsyncMock, MagicMock  # noqa: PLC0415

    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = QdrantAdapter()

    def make_record(text: str) -> MagicMock:
        r = MagicMock()
        r.payload = {"text": text}
        return r

    page1 = [make_record("chunk-1")]
    page2 = [make_record("chunk-2")]
    mock_client = AsyncMock()
    mock_client.scroll = AsyncMock(side_effect=[(page1, "cursor-1"), (page2, None)])
    adapter._client = mock_client

    results = await adapter.scroll_by_source("s1", "t1")

    assert len(results) == 2
    assert mock_client.scroll.call_count == 2
