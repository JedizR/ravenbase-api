# src/workers/ingestion_tasks.py
from __future__ import annotations

import io
import re
import uuid
import zipfile
from datetime import UTC, datetime

import structlog
from qdrant_client.models import PointStruct

from src.adapters.docling_adapter import DoclingAdapter
from src.adapters.moderation_adapter import ModerationAdapter, ModerationError
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.adapters.storage_adapter import StorageAdapter
from src.api.dependencies.db import async_session_factory
from src.models.source import Source, SourceStatus
from src.models.user import User
from src.workers.utils import publish_progress

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# DB helpers — open their own sessions (no Depends() in worker context)
# ---------------------------------------------------------------------------


async def _update_source_status(source_id: str, status: SourceStatus) -> None:
    async with async_session_factory() as session:
        source = await session.get(Source, uuid.UUID(source_id))
        if source is None:
            logger.warning("_update_source_status.not_found", source_id=source_id)
            return
        source.status = status
        session.add(source)
        await session.commit()


async def _set_source_failed(source_id: str, error_message: str) -> None:
    async with async_session_factory() as session:
        source = await session.get(Source, uuid.UUID(source_id))
        if source is None:
            return
        source.status = SourceStatus.FAILED
        source.error_message = error_message[:1000]  # cap length
        session.add(source)
        await session.commit()


async def _set_source_completed(source_id: str, chunk_count: int) -> None:
    async with async_session_factory() as session:
        source = await session.get(Source, uuid.UUID(source_id))
        if source is None:
            return
        source.status = SourceStatus.COMPLETED
        source.chunk_count = chunk_count
        source.completed_at = datetime.now(UTC)
        session.add(source)
        await session.commit()


async def _flag_user_account(tenant_id: str) -> None:
    """Set user.is_active = False on hard-reject moderation (AC-11)."""
    async with async_session_factory() as session:
        user = await session.get(User, uuid.UUID(tenant_id))
        if user is None:
            logger.warning("_flag_user_account.not_found", tenant_id=tenant_id)
            return
        user.is_active = False
        session.add(user)
        await session.commit()


# ---------------------------------------------------------------------------
# Text preview helper — for moderation pre-check (runs before Docling)
# ---------------------------------------------------------------------------


def _extract_text_preview(content: bytes, mime_type: str, max_chars: int = 4000) -> str:
    """Fast text extraction for moderation — does NOT use Docling.

    - text/plain: UTF-8 decode
    - DOCX: unzip + strip XML from word/document.xml
    - PDF / unknown: printable ASCII from raw bytes
    """
    if mime_type == "text/plain":
        return content.decode("utf-8", errors="ignore")[:max_chars]

    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if "word/document.xml" in z.namelist():
                    xml_bytes = z.read("word/document.xml")
                    xml_str = xml_bytes.decode("utf-8", errors="ignore")
                    text = re.sub(r"<[^>]+>", " ", xml_str)
                    return " ".join(text.split())[:max_chars]
        except Exception:
            pass  # fall through to generic extraction

    # PDF or fallback: printable ASCII chars from raw bytes
    raw = content.decode("latin-1", errors="ignore")
    printable = "".join(c for c in raw if 32 <= ord(c) < 127 or c in "\n\t")
    return " ".join(printable.split())[:max_chars]


# ---------------------------------------------------------------------------
# Worker task
# ---------------------------------------------------------------------------


async def parse_document(
    ctx: dict,  # type: ignore[type-arg]
    *,
    source_id: str,
    tenant_id: str,
) -> dict:  # type: ignore[type-arg]
    """Parse, chunk, embed, and index an uploaded document.

    Status transitions: PENDING → PROCESSING → INDEXING → COMPLETED
    On any failure: FAILED (no re-raise → no ARQ retry, per AC-8).
    Progress published to Redis pub/sub channel `job:progress:{source_id}`.
    """
    log = logger.bind(source_id=source_id, tenant_id=tenant_id)
    log.info("parse_document.started")

    try:
        # ── 1. Load Source record ───────────────────────────────────────────
        async with async_session_factory() as session:
            source = await session.get(Source, uuid.UUID(source_id))
            if source is None:
                log.error("parse_document.source_not_found")
                return {"status": "error", "source_id": source_id, "reason": "not_found"}
            storage_path: str = source.storage_path
            mime_type: str = source.mime_type
            original_filename: str = source.original_filename
            profile_id: str | None = str(source.profile_id) if source.profile_id else None

        # ── 2. PROCESSING ───────────────────────────────────────────────────
        await _update_source_status(source_id, SourceStatus.PROCESSING)
        await publish_progress(source_id, 5, "Downloading file...", "processing")

        # ── 3. Download from Supabase Storage ──────────────────────────────
        content = await StorageAdapter().download_file(storage_path)
        log.info("parse_document.downloaded", size_bytes=len(content))

        # ── 4. Content moderation (AC-11) — BEFORE Docling ─────────────────
        await publish_progress(source_id, 10, "Checking content safety...", "processing")
        preview = _extract_text_preview(content, mime_type)
        try:
            await ModerationAdapter().check_content(preview, source_id, tenant_id)
        except ModerationError as mod_err:
            await _set_source_failed(source_id, "Content flagged by safety system")
            await publish_progress(source_id, 0, "Content flagged by safety system", "failed")
            if mod_err.hard:
                await _flag_user_account(tenant_id)
                log.warning("parse_document.moderation_hard_reject")
            else:
                log.warning("parse_document.moderation_soft_reject")
            return {"status": "failed_moderation", "source_id": source_id}

        # ── 5. Parse + chunk via Docling (in executor) ──────────────────────
        await publish_progress(source_id, 20, "Parsing document...", "processing")
        chunks = await DoclingAdapter().parse_and_chunk(content, original_filename)
        log.info("parse_document.parsed", chunk_count=len(chunks))

        if not chunks:
            await _set_source_failed(source_id, "No content extracted from document")
            await publish_progress(source_id, 0, "No content extracted", "failed")
            return {"status": "error", "source_id": source_id, "reason": "empty_document"}

        # ── 6. INDEXING ─────────────────────────────────────────────────────
        await _update_source_status(source_id, SourceStatus.INDEXING)
        await publish_progress(source_id, 50, "Generating embeddings...", "indexing")

        # ── 7. Embed chunks (batched 100) ────────────────────────────────────
        texts = [c["text"] for c in chunks]
        embeddings = await OpenAIAdapter().embed_chunks(texts)

        await publish_progress(source_id, 75, "Indexing in vector store...", "indexing")

        # ── 8. Upsert to Qdrant (tenant-scoped) ──────────────────────────────
        now_iso = datetime.now(UTC).isoformat()
        points = [
            PointStruct(
                # Deterministic UUID → safe to re-run (upsert overwrites)
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")),
                vector=embeddings[i],
                payload={
                    "tenant_id": tenant_id,
                    "source_id": source_id,
                    "chunk_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")),
                    "profile_id": profile_id,
                    "page_number": chunks[i].get("page_number", 0),
                    "chunk_index": i,
                    "text": chunks[i]["text"],
                    "created_at": now_iso,
                },
            )
            for i in range(len(chunks))
        ]
        await QdrantAdapter().upsert(points)
        log.info("parse_document.indexed", point_count=len(points))

        # ── 9. COMPLETED ─────────────────────────────────────────────────────
        await _set_source_completed(source_id, chunk_count=len(chunks))
        await publish_progress(source_id, 100, "Ingestion complete!", "completed")

        # ── 10. Enqueue graph_extraction (AC-10) ──────────────────────────────
        await ctx["redis"].enqueue_job(
            "graph_extraction",
            source_id=source_id,
            tenant_id=tenant_id,
        )
        log.info("parse_document.graph_extraction_enqueued")

        log.info("parse_document.completed", chunk_count=len(chunks))
        return {"status": "ok", "source_id": source_id, "chunk_count": len(chunks)}

    except Exception as exc:
        # Catch-all: set FAILED, log, do NOT re-raise (prevents ARQ retry — AC-8)
        log.error("parse_document.failed", error=str(exc), exc_info=True)
        try:
            await _set_source_failed(source_id, str(exc))
            await publish_progress(source_id, 0, f"Ingestion failed: {exc}", "failed")
        except Exception as inner:
            log.error("parse_document.cleanup_failed", error=str(inner))
        return {"status": "error", "source_id": source_id, "error": str(exc)}
