import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_download_file_returns_bytes() -> None:
    """download_file returns the bytes fetched from Supabase Storage."""
    fake_bytes = b"%PDF-1.4 fake content"

    with patch("src.adapters.storage_adapter.StorageAdapter._get_client") as mock_client:
        mock_storage = MagicMock()
        mock_storage.from_.return_value.download.return_value = fake_bytes
        mock_client.return_value.storage = mock_storage

        from src.adapters.storage_adapter import StorageAdapter

        adapter = StorageAdapter()
        result = await adapter.download_file("/tenant/source/file.pdf")

    assert result == fake_bytes


@pytest.mark.asyncio
async def test_download_file_raises_on_failure() -> None:
    """download_file raises RuntimeError when Supabase call fails."""
    with patch("src.adapters.storage_adapter.StorageAdapter._get_client") as mock_client:
        mock_storage = MagicMock()
        mock_storage.from_.return_value.download.side_effect = Exception("network error")
        mock_client.return_value.storage = mock_storage

        from src.adapters.storage_adapter import StorageAdapter

        adapter = StorageAdapter()
        with pytest.raises(RuntimeError, match="Supabase Storage download failed"):
            await adapter.download_file("/tenant/source/file.pdf")
