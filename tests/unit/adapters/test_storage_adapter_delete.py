# tests/unit/adapters/test_storage_adapter_delete.py
from unittest.mock import MagicMock

import pytest

from src.adapters.storage_adapter import StorageAdapter


@pytest.mark.asyncio
async def test_delete_folder_by_tenant_deletes_all_files():
    """delete_folder_by_tenant lists all files then removes them."""
    adapter = StorageAdapter()

    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket

    # Simulate two source-level subdirectories, each with one file
    mock_bucket.list.side_effect = [
        [{"name": "src_abc", "id": None, "metadata": None}],  # top-level: source dirs
        [{"name": "file.pdf", "id": "f1", "metadata": {}}],  # files in src_abc
    ]
    mock_bucket.remove.return_value = []

    adapter._client = mock_client

    await adapter.delete_folder_by_tenant(tenant_id="user-123")

    # Should have listed root folder then the subfolder
    assert mock_bucket.list.call_count == 2
    # Should have removed the file inside the subfolder
    mock_bucket.remove.assert_called_once_with(["user-123/src_abc/file.pdf"])


@pytest.mark.asyncio
async def test_delete_folder_by_tenant_handles_empty_folder():
    """delete_folder_by_tenant does nothing if folder is empty."""
    adapter = StorageAdapter()
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_client.storage.from_.return_value = mock_bucket
    mock_bucket.list.return_value = []
    adapter._client = mock_client

    await adapter.delete_folder_by_tenant(tenant_id="user-empty")

    mock_bucket.remove.assert_not_called()
