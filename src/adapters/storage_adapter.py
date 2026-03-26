import structlog

from src.adapters.base import BaseAdapter
from src.core.config import settings

logger = structlog.get_logger()


class StorageAdapter(BaseAdapter):
    """Wraps Supabase Storage for file upload/delete operations."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):  # type: ignore[return]
        if self._client is None:
            from supabase import create_client  # noqa: PLC0415

            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
            )
        return self._client

    async def upload_file(self, content: bytes, path: str) -> str:
        """Upload bytes to Supabase Storage at the given path.

        Args:
            content: Raw file bytes.
            path: Storage path, e.g. "/{tenant_id}/{source_id}/{filename}".

        Returns:
            The storage path on success.

        Raises:
            RuntimeError: If the upload fails.
        """
        log = logger.bind(storage_path=path, size_bytes=len(content))
        log.info("storage.upload.started")
        try:
            client = self._get_client()
            client.storage.from_(settings.STORAGE_BUCKET).upload(
                path=path,
                file=content,
                file_options={"upsert": "false"},
            )
            log.info("storage.upload.completed")
            return path
        except Exception as exc:
            log.error("storage.upload.failed", error=str(exc))
            raise RuntimeError(f"Supabase Storage upload failed: {exc}") from exc

    async def download_file(self, path: str) -> bytes:
        """Download bytes from Supabase Storage at the given path.

        Args:
            path: Storage path, e.g. "/{tenant_id}/{source_id}/{filename}".

        Returns:
            Raw file bytes.

        Raises:
            RuntimeError: If the download fails.
        """
        log = logger.bind(storage_path=path)
        log.info("storage.download.started")
        try:
            client = self._get_client()
            data = client.storage.from_(settings.STORAGE_BUCKET).download(path)
            log.info("storage.download.completed", size_bytes=len(data))
            return data
        except Exception as exc:
            log.error("storage.download.failed", error=str(exc))
            raise RuntimeError(f"Supabase Storage download failed: {exc}") from exc
