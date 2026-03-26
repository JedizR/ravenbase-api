# tests/unit/adapters/test_neo4j_adapter.py
from unittest.mock import AsyncMock, MagicMock

import pytest


def test_init_does_not_open_connection() -> None:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = Neo4jAdapter()
    assert adapter._driver is None


@pytest.mark.asyncio
async def test_run_query_passes_params_to_session() -> None:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = Neo4jAdapter()

    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"n": "val"}])
    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_cm)
    adapter._driver = mock_driver

    cypher = "MATCH (m:Memory) WHERE m.tenant_id = $tenant_id RETURN m"
    result = await adapter.run_query(cypher, tenant_id="user-abc")

    mock_session.run.assert_called_once()
    _, call_kwargs = mock_session.run.call_args
    assert call_kwargs.get("tenant_id") == "user-abc" or (
        "user-abc" in str(mock_session.run.call_args)
    )
    assert result == [{"n": "val"}]


@pytest.mark.asyncio
async def test_verify_connectivity_returns_true_on_success() -> None:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = Neo4jAdapter()
    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock()
    adapter._driver = mock_driver

    assert await adapter.verify_connectivity() is True


@pytest.mark.asyncio
async def test_verify_connectivity_returns_false_on_error() -> None:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = Neo4jAdapter()
    mock_driver = AsyncMock()
    mock_driver.verify_connectivity = AsyncMock(side_effect=Exception("unreachable"))
    adapter._driver = mock_driver

    assert await adapter.verify_connectivity() is False


def test_cleanup_clears_driver() -> None:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = Neo4jAdapter()
    adapter._driver = AsyncMock()
    adapter.cleanup()
    assert adapter._driver is None


@pytest.mark.asyncio
async def test_write_nodes_includes_tenant_id_param() -> None:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = Neo4jAdapter()
    adapter.run_query = AsyncMock()

    await adapter.write_nodes(
        label="Memory",
        node_id_key="memory_id",
        properties={"memory_id": "m-1", "content": "hello"},
        tenant_id="user-abc",
    )

    adapter.run_query.assert_called_once()
    _, call_kwargs = adapter.run_query.call_args
    assert call_kwargs.get("tenant_id") == "user-abc"
