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
    call_args = mock_session.run.call_args
    # run_query passes params as a positional dict: session.run(query, params_dict)
    positional_args = call_args.args
    assert len(positional_args) == 2, "session.run should be called with (query, params_dict)"
    assert positional_args[0] == cypher
    params_dict = positional_args[1]
    assert isinstance(params_dict, dict)
    assert params_dict.get("tenant_id") == "user-abc"
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


@pytest.mark.asyncio
async def test_write_nodes_raises_on_invalid_label() -> None:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = Neo4jAdapter()
    adapter.run_query = AsyncMock()

    with pytest.raises(ValueError, match="Invalid Neo4j node label"):
        await adapter.write_nodes(
            label="Injected; DROP DATABASE neo4j",
            node_id_key="memory_id",
            properties={"memory_id": "m-1"},
            tenant_id="user-abc",
        )

    adapter.run_query.assert_not_called()


@pytest.mark.asyncio
async def test_write_relationships_raises_on_invalid_rel_type() -> None:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = Neo4jAdapter()
    adapter.run_query = AsyncMock()

    with pytest.raises(ValueError, match="Invalid Neo4j relationship type"):
        await adapter.write_relationships(
            from_label="Memory",
            from_id_key="memory_id",
            from_id="m-1",
            to_label="Concept",
            to_id_key="concept_id",
            to_id="c-1",
            rel_type="MALICIOUS_TYPE; DROP DATABASE",
            tenant_id="user-abc",
        )

    adapter.run_query.assert_not_called()
