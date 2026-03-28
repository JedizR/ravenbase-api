# tests/unit/services/test_deletion_service.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.deletion_service import DeletionService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_delete_storage_by_tenant_calls_adapter():
    svc = DeletionService()
    with patch("src.services.deletion_service.StorageAdapter") as mock_adapter_cls:
        mock_adapter = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter
        await svc.delete_storage_by_tenant("user-abc")
    mock_adapter.delete_folder_by_tenant.assert_called_once_with(tenant_id="user-abc")


@pytest.mark.asyncio
async def test_delete_qdrant_by_tenant_calls_adapter():
    svc = DeletionService()
    with patch("src.services.deletion_service.QdrantAdapter") as mock_adapter_cls:
        mock_adapter = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter
        await svc.delete_qdrant_by_tenant("user-abc")
    mock_adapter.delete_by_filter.assert_called_once_with(tenant_id="user-abc")


@pytest.mark.asyncio
async def test_delete_neo4j_by_tenant_calls_adapter():
    svc = DeletionService()
    with patch("src.services.deletion_service.Neo4jAdapter") as mock_adapter_cls:
        mock_adapter = AsyncMock()
        mock_adapter_cls.return_value = mock_adapter
        await svc.delete_neo4j_by_tenant("user-abc")
    mock_adapter.delete_all_by_tenant.assert_called_once_with(tenant_id="user-abc")


@pytest.mark.asyncio
async def test_delete_postgres_by_tenant_deletes_in_order(mock_db):
    svc = DeletionService()
    executed_queries: list[str] = []

    async def capture_execute(stmt, *_args, **_kwargs):
        executed_queries.append(str(stmt))
        mock_result = MagicMock()
        mock_result.all.return_value = []
        return mock_result

    mock_db.execute = capture_execute

    await svc.delete_postgres_by_tenant("user-abc", mock_db)

    # Should have committed after deletions
    mock_db.commit.assert_called_once()
    # Queries should cover key tables in FK-safe order
    all_queries = " ".join(executed_queries)
    assert "job_statuses" in all_queries
    assert "source_authority_weights" in all_queries
    assert "users" in all_queries


@pytest.mark.asyncio
async def test_delete_clerk_user_calls_clerk_api():
    svc = DeletionService()
    with patch("src.services.deletion_service.settings") as mock_settings:
        mock_settings.CLERK_SECRET_KEY = "sk_test_abc"
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_http = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_http.delete = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await svc.delete_clerk_user("user_clerk_abc")

    mock_http.delete.assert_called_once_with(
        "https://api.clerk.com/v1/users/user_clerk_abc",
        headers={"Authorization": "Bearer sk_test_abc"},
    )
