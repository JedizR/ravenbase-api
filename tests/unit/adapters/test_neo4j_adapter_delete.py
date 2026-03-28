# tests/unit/adapters/test_neo4j_adapter_delete.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.neo4j_adapter import Neo4jAdapter


@pytest.mark.asyncio
async def test_delete_all_by_tenant_runs_two_queries():
    """delete_all_by_tenant deletes tenant nodes then the User node."""
    adapter = Neo4jAdapter()

    mock_session = AsyncMock()
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])
    mock_session.run = AsyncMock(return_value=mock_result)

    mock_driver = MagicMock()
    mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

    adapter._driver = mock_driver

    await adapter.delete_all_by_tenant(tenant_id="user-123")

    assert mock_session.run.call_count == 2
    first_call_query = mock_session.run.call_args_list[0][0][0]
    second_call_query = mock_session.run.call_args_list[1][0][0]
    assert "DETACH DELETE" in first_call_query
    assert "tenant_id" in first_call_query
    assert "User" in second_call_query
    assert "user_id" in second_call_query
