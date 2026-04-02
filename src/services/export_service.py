# src/services/export_service.py
"""ExportService — GDPR Article 20 Right to Data Portability.

Collects all user data from PostgreSQL, Neo4j, and Supabase Storage,
assembles into a ZIP, uploads to exports bucket, generates pre-signed URL.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.storage_adapter import StorageAdapter
from src.core.config import settings
from src.services.base import BaseService

logger = structlog.get_logger()

EXPORT_BUCKET = "exports"
DOWNLOAD_URL_EXPIRY_HOURS = 72
PARTIAL_EXPORT_FILENAME = "PARTIAL_EXPORT.txt"


class ExportService(BaseService):
    """Collects and packages all user data for GDPR portability."""

    async def collect_postgres_export(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        """Collect all PostgreSQL user data as JSON dict.

        Returns: {sources: [...], meta_documents: [...], profiles: [...], chat_sessions: [...]}
        """
        log = logger.bind(user_id=user_id, step="postgres_export")
        log.info("export.postgres.started")

        result: dict[str, Any] = {}

        try:
            # Sources
            sources_result = await db.execute(
                text("""
                    SELECT id, original_filename, file_type, mime_type,
                           file_size_bytes, status, chunk_count, node_count,
                           ingested_at, completed_at, storage_path
                    FROM sources WHERE user_id = :uid
                    ORDER BY ingested_at DESC
                """),
                {"uid": user_id},
            )
            result["sources"] = [dict(row) for row in sources_result.mappings()]
        except Exception as exc:
            log.warning("export.postgres.sources_failed", error=str(exc))
            result["sources"] = []

        try:
            # Meta-documents
            meta_result = await db.execute(
                text("""
                    SELECT id, title, content, created_at, updated_at
                    FROM meta_documents WHERE user_id = :uid
                    ORDER BY created_at DESC
                """),
                {"uid": user_id},
            )
            result["meta_documents"] = [dict(row) for row in meta_result.mappings()]
        except Exception as exc:
            log.warning("export.postgres.meta_documents_failed", error=str(exc))
            result["meta_documents"] = []

        try:
            # Profiles
            profiles_result = await db.execute(
                text("SELECT * FROM system_profiles WHERE user_id = :uid"),
                {"uid": user_id},
            )
            result["profiles"] = [dict(row) for row in profiles_result.mappings()]
        except Exception as exc:
            log.warning("export.postgres.profiles_failed", error=str(exc))
            result["profiles"] = []

        try:
            # Chat sessions
            sessions_result = await db.execute(
                text(
                    "SELECT id, title, created_at, updated_at "
                    "FROM chat_sessions WHERE user_id = :uid"
                ),
                {"uid": user_id},
            )
            result["chat_sessions"] = [dict(row) for row in sessions_result.mappings()]
        except Exception as exc:
            log.warning("export.postgres.chat_sessions_failed", error=str(exc))
            result["chat_sessions"] = []

        log.info("export.postgres.completed", record_counts={k: len(v) for k, v in result.items()})
        return result

    async def collect_neo4j_export(self, user_id: str) -> dict[str, Any]:
        """Collect all Neo4j nodes and relationships for tenant as JSON.

        Does NOT include Qdrant vectors (derived data, not user data per GDPR).
        """
        log = logger.bind(user_id=user_id, step="neo4j_export")
        log.info("export.neo4j.started")

        try:
            adapter = Neo4jAdapter()
            nodes = await adapter.get_all_nodes_by_tenant(user_id)
            rels = await adapter.get_all_relationships_by_tenant(user_id)
            log.info("export.neo4j.completed", node_count=len(nodes), rel_count=len(rels))
            return {"nodes": nodes, "relationships": rels}
        except Exception as exc:
            log.warning("export.neo4j.failed", error=str(exc))
            return {"nodes": [], "relationships": [], "_error": str(exc)}

    async def collect_storage_files(
        self, user_id: str, storage_paths: list[str]
    ) -> dict[str, bytes]:
        """Download original uploaded files from Supabase Storage.

        Returns: {storage_path: bytes_content}
        """
        log = logger.bind(user_id=user_id, step="storage_export")
        log.info("export.storage.started", file_count=len(storage_paths))

        storage_adapter = StorageAdapter()
        downloaded: dict[str, bytes] = {}
        failed: list[str] = []

        for path in storage_paths:
            try:
                content = await storage_adapter.download_file(path)
                downloaded[path] = content
            except Exception as exc:
                log.warning("export.storage.file_failed", path=path, error=str(exc))
                failed.append(path)

        log.info("export.storage.completed", downloaded=len(downloaded), failed=len(failed))
        return downloaded

    async def create_export_zip(
        self,
        postgres_data: dict[str, Any],
        neo4j_data: dict[str, Any],
        storage_files: dict[str, bytes],
        partial_components: list[str],
    ) -> bytes:
        """Assemble all collected data into a ZIP file.

        partial_components: list of component names that failed (for PARTIAL_EXPORT.txt)
        """
        log = logger.bind(step="zip_assembly")
        log.info("export.zip.started")

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write README
            readme = f"""\
Ravenbase Data Export
Generated: {datetime.now(UTC).isoformat()}

Contents:
- sources/ — Original uploaded files (from Supabase Storage)
- data/ — Structured data exports (JSON)
  - sources.json
  - meta_documents.json
  - profiles.json
  - chat_sessions.json
- graph_export.json — Knowledge graph (Neo4j)

Total storage files: {len(storage_files)}
"""
            zf.writestr("README.txt", readme)

            # Write JSON data files
            for key, value in postgres_data.items():
                zf.writestr(f"data/{key}.json", json.dumps(value, indent=2, default=str))

            # Write Neo4j graph
            zf.writestr("graph_export.json", json.dumps(neo4j_data, indent=2, default=str))

            # Write original files into sources/
            for path, content in storage_files.items():
                filename = path.split("/")[-1]
                zf.writestr(f"sources/{filename}", content)

            # Write PARTIAL_EXPORT.txt if any component failed
            if partial_components:
                partial_txt = "PARTIAL EXPORT - Some components could not be exported:\n\n"
                for comp in partial_components:
                    partial_txt += f"- {comp}: export failed (see error logs)\n"
                partial_txt += "\nYour export is still usable with the available data.\n"
                zf.writestr(PARTIAL_EXPORT_FILENAME, partial_txt)

        log.info("export.zip.completed", size_bytes=buffer.tell())
        return buffer.getvalue()

    async def upload_zip(self, user_id: str, zip_content: bytes) -> str:
        """Upload ZIP to Supabase Storage at exports/{user_id}/{timestamp}.zip.

        Returns the storage path.
        """
        log = logger.bind(user_id=user_id, step="zip_upload")
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        path = f"exports/{user_id}/{timestamp}.zip"

        log.info("export.upload.started", path=path, size_bytes=len(zip_content))
        adapter = StorageAdapter()
        await adapter.upload_file(zip_content, path)
        log.info("export.upload.completed", path=path)
        return path

    async def generate_presigned_url(self, storage_path: str) -> str:
        """Generate a pre-signed download URL with 72-hour expiry.

        Uses Supabase Storage createSignedUrl.
        """
        log = logger.bind(storage_path=storage_path, step="presigned_url")

        from supabase import create_client  # noqa: PLC0415

        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        bucket = client.storage.from_(EXPORT_BUCKET)

        # create_signed_url takes (path, expires_in_seconds)
        signed_url_response = bucket.create_signed_url(
            storage_path, expires_in=DOWNLOAD_URL_EXPIRY_HOURS * 3600
        )
        log.info("export.presigned_url.generated", expires_hours=DOWNLOAD_URL_EXPIRY_HOURS)
        # Supabase client returns SignedUrlResponse with signed_url attr, or just a URL string
        return getattr(signed_url_response, "signed_url", None) or str(signed_url_response)  # type: ignore[return-value]

    async def export_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        export_format: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> dict[str, Any]:
        """Main export orchestrator.

        progress_callback(progress: int, status: str) for real-time updates.
        Returns: {status, download_url, progress, error}
        """
        log = logger.bind(user_id=user_id, export_format=export_format)
        log.info("export.started")

        partial_components: list[str] = []
        result: dict[str, Any] = {"status": "preparing", "progress": 0}

        def update_progress(progress: int, status: str) -> None:
            result["progress"] = progress
            result["status"] = status
            if progress_callback:
                progress_callback(progress, status)

        try:
            # Phase 1: Collect PostgreSQL data (20%)
            update_progress(5, "preparing")
            postgres_data = await self.collect_postgres_export(db, user_id)
            update_progress(20, "preparing")

            # Phase 2: Collect Neo4j data (40%)
            neo4j_data = await self.collect_neo4j_export(user_id)
            if neo4j_data.get("_error"):
                partial_components.append("Knowledge Graph (Neo4j)")
            update_progress(40, "preparing")

            # Phase 3: Download original storage files (70%)
            # Get storage paths from sources
            storage_paths = [
                s["storage_path"] for s in postgres_data.get("sources", []) if s.get("storage_path")
            ]
            storage_files = await self.collect_storage_files(user_id, storage_paths)
            update_progress(70, "preparing")

            # Phase 4: Create ZIP (85%)
            zip_content = await self.create_export_zip(
                postgres_data, neo4j_data, storage_files, partial_components
            )
            update_progress(85, "preparing")

            # Phase 5: Upload to Storage (95%)
            storage_path = await self.upload_zip(user_id, zip_content)
            update_progress(95, "preparing")

            # Phase 6: Generate pre-signed URL
            download_url = await self.generate_presigned_url(storage_path)
            update_progress(100, "ready")

            result["status"] = "ready"
            result["download_url"] = download_url
            log.info("export.completed", download_url=download_url[:50] + "...")

        except Exception as exc:
            log.error("export.failed", error=str(exc), exc_info=True)
            result["status"] = "failed"
            result["error"] = str(exc)

        return result
