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

    async def delete_folder_by_tenant(self, tenant_id: str) -> None:
        """Delete all Supabase Storage files under /{tenant_id}/.

        Lists top-level items (source_id subfolders), then lists and removes
        files within each subfolder. Matches storage_path format:
        /{tenant_id}/{source_id}/{filename}

        Raises the first exception encountered after logging it (outer
        try/except, no per-subfolder recovery).
        """
        if not tenant_id:
            raise ValueError("tenant_id must not be empty")
        log = logger.bind(tenant_id=tenant_id, action="gdpr_deletion", step="storage")
        log.info("storage.delete_by_tenant.started")
        try:
            client = self._get_client()
            bucket = client.storage.from_(settings.STORAGE_BUCKET)

            # List top-level items (source_id directories)
            top_level = bucket.list(path=tenant_id)
            if not top_level:
                log.info("storage.delete_by_tenant.empty")
                return

            for item in top_level:
                item_name = item.get("name", "")
                if not item_name:
                    continue
                subfolder_path = f"{tenant_id}/{item_name}"
                # If the item has no metadata id it's a "folder" prefix
                if item.get("id") is None:
                    # List files inside the subfolder
                    sub_files = bucket.list(path=subfolder_path)
                    paths = [f"{subfolder_path}/{f['name']}" for f in sub_files if f.get("id")]
                    if paths:
                        bucket.remove(paths)
                else:
                    # Item is a file at the top level
                    bucket.remove([subfolder_path])

            log.info("storage.delete_by_tenant.completed")
        except Exception as exc:
            log.error("storage.delete_by_tenant.failed", error=str(exc))
            raise
