# tests/unit/workers/test_deletion_tasks.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_cascade_delete_account_calls_all_steps():
    """All 5 deletion steps are called in the correct order."""
    from src.workers.deletion_tasks import cascade_delete_account  # noqa: PLC0415

    mock_ctx: dict = {}
    order: list[str] = []

    mock_svc = MagicMock()

    async def fake_storage(uid: str) -> None:
        order.append("storage")

    async def fake_qdrant(uid: str) -> None:
        order.append("qdrant")

    async def fake_neo4j(uid: str) -> None:
        order.append("neo4j")

    async def fake_postgres(uid: str, db) -> None:
        order.append("postgres")

    async def fake_clerk(uid: str) -> None:
        order.append("clerk")

    mock_svc.delete_storage_by_tenant = fake_storage
    mock_svc.delete_qdrant_by_tenant = fake_qdrant
    mock_svc.delete_neo4j_by_tenant = fake_neo4j
    mock_svc.delete_postgres_by_tenant = fake_postgres
    mock_svc.delete_clerk_user = fake_clerk

    mock_db = AsyncMock()

    with patch("src.workers.deletion_tasks.DeletionService", return_value=mock_svc):
        with patch("src.workers.deletion_tasks.async_session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await cascade_delete_account(mock_ctx, user_id="user-abc")

    assert order == ["storage", "qdrant", "neo4j", "postgres", "clerk"]
    assert result["status"] == "deleted"
    assert result["user_id"] == "user-abc"


@pytest.mark.asyncio
async def test_cascade_delete_account_continues_on_partial_failure():
    """If one step raises, the cascade continues and still calls remaining steps."""
    from src.workers.deletion_tasks import cascade_delete_account  # noqa: PLC0415

    mock_ctx: dict = {}
    order: list[str] = []

    mock_svc = MagicMock()
    storage_called = False

    async def fail_storage(uid: str) -> None:
        nonlocal storage_called
        storage_called = True
        raise RuntimeError("S3 timeout")

    async def fake_qdrant(uid: str) -> None:
        order.append("qdrant")

    async def fake_neo4j(uid: str) -> None:
        order.append("neo4j")

    async def fake_postgres(uid: str, db) -> None:
        order.append("postgres")

    async def fake_clerk(uid: str) -> None:
        order.append("clerk")

    mock_svc.delete_storage_by_tenant = fail_storage
    mock_svc.delete_qdrant_by_tenant = fake_qdrant
    mock_svc.delete_neo4j_by_tenant = fake_neo4j
    mock_svc.delete_postgres_by_tenant = fake_postgres
    mock_svc.delete_clerk_user = fake_clerk

    mock_db = AsyncMock()

    with patch("src.workers.deletion_tasks.DeletionService", return_value=mock_svc):
        with patch("src.workers.deletion_tasks.async_session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await cascade_delete_account(mock_ctx, user_id="user-abc")

    # Even though storage failed, all subsequent steps ran
    assert storage_called, "storage step was not attempted before failing"
    assert "qdrant" in order
    assert "neo4j" in order
    assert "postgres" in order
    assert "clerk" in order
    assert result["status"] == "deleted"
