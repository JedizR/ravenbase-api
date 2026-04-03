# src/workers/ingestion_tasks.py
from __future__ import annotations

import io
import re
import uuid
import zipfile
from datetime import datetime

import structlog
from fastapi import HTTPException
from qdrant_client.models import PointStruct

from src.adapters.docling_adapter import DoclingAdapter
from src.adapters.moderation_adapter import ModerationAdapter, ModerationError
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.adapters.storage_adapter import StorageAdapter
from src.api.dependencies.db import async_session_factory
from src.models.source import Source, SourceStatus
from src.models.user import User
from src.services.credit_service import CreditService
from src.services.referral_service import ReferralService
from src.workers.utils import publish_progress

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Plain-text chunking — used by ingest_text (no Docling)
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 2000  # chars (~500 tokens at 4 chars/token)
_CHUNK_OVERLAP = 200  # chars


def _chunk_plain_text(content: str) -> list[dict[str, object]]:
    """Split plain text into overlapping fixed-size chunks.

    Returns a list of dicts: [{"text": str, "chunk_index": int}]
    Single chunk returned when content fits within _CHUNK_SIZE.
    """
    if len(content) <= _CHUNK_SIZE:
        return [{"text": content, "chunk_index": 0}]

    chunks: list[dict[str, object]] = []
    start = 0
    idx = 0
    while start < len(content):
        end = min(start + _CHUNK_SIZE, len(content))
        chunks.append({"text": content[start:end], "chunk_index": idx})
        if end == len(content):
            break
        start = end - _CHUNK_OVERLAP
        idx += 1
    return chunks


# ---------------------------------------------------------------------------
# DB helpers — open their own sessions (no Depends() in worker context)
# ---------------------------------------------------------------------------


async def _update_source_status(source_id: str, status: str) -> None:
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
        source.completed_at = datetime.utcnow()
        session.add(source)
        await session.commit()


async def _flag_user_account(tenant_id: str) -> None:
    """Set user.is_active = False on hard-reject moderation (AC-11)."""
    async with async_session_factory() as session:
        user = await session.get(User, tenant_id)
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
        except Exception as exc:  # noqa: BLE001
            logger.warning("ingestion.zip_parse_fallback", error=str(exc))
            # fall through to generic extraction

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
        now_iso = datetime.utcnow().isoformat()
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
        qdrant = QdrantAdapter()
        await qdrant.ensure_collection()
        await qdrant.upsert(points)
        log.info("parse_document.indexed", point_count=len(points))

        # ── Credit deduction: 1 per page (AFTER successful indexing) ────────
        page_numbers = {c.get("page_number", 0) for c in chunks}
        page_count = max(1, len(page_numbers))
        async with async_session_factory() as credit_session:
            try:
                await CreditService().deduct(
                    credit_session,
                    tenant_id,
                    amount=page_count,
                    operation="ingestion",
                    reference_id=uuid.UUID(source_id),
                )
                log.info("parse_document.credits_deducted", pages=page_count)
            except HTTPException as credit_exc:
                if credit_exc.status_code == 402:
                    # Insufficient credits: document is already indexed — log and continue
                    log.warning("parse_document.insufficient_credits", pages=page_count)
                else:
                    log.error("parse_document.credit_deduction_failed", error=str(credit_exc))
                    raise
            except Exception as credit_exc:
                log.error(
                    "parse_document.credit_deduction_failed", error=str(credit_exc), exc_info=True
                )
                raise

        # ── 9. COMPLETED ─────────────────────────────────────────────────────
        await _set_source_completed(source_id, chunk_count=len(chunks))
        await publish_progress(source_id, 100, "Ingestion complete!", "completed")

        # ── 9b. Award referrer if this is referee's first upload (AC-4, AC-5, AC-6, AC-7) ──
        try:
            async with async_session_factory() as referral_session:
                await ReferralService().award_referrer_on_first_upload(
                    referral_session,
                    referee_user_id=tenant_id,
                )
        except Exception as referral_exc:
            # Non-fatal: log and continue — ingestion job must not fail
            logger.warning(
                "parse_document.referral_award_failed",
                tenant_id=tenant_id,
                source_id=source_id,
                error=str(referral_exc),
            )

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


async def ingest_text(
    ctx: dict,  # type: ignore[type-arg]
    *,
    content: str,
    profile_id: str | None,
    tags: list[str],
    tenant_id: str,
    source_id: str,
) -> dict:  # type: ignore[type-arg]
    """Chunk, embed, and index plain text from the Omnibar quick-capture.

    No Docling. No StorageAdapter. Status: PENDING → PROCESSING → INDEXING → COMPLETED.
    On failure: FAILED (no re-raise → no ARQ retry).
    """
    log = logger.bind(tenant_id=tenant_id, source_id=source_id, job="ingest_text")
    log.info("ingest_text.started", char_count=len(content))

    try:
        # ── 1. PROCESSING ───────────────────────────────────────────────────
        await _update_source_status(source_id, SourceStatus.PROCESSING)
        await publish_progress(source_id, 10, "Chunking text...", "processing")

        # ── 2. Chunk plain text ──────────────────────────────────────────────
        chunks = _chunk_plain_text(content)
        log.info("ingest_text.chunked", chunk_count=len(chunks))

        # ── 3. INDEXING ──────────────────────────────────────────────────────
        await _update_source_status(source_id, SourceStatus.INDEXING)
        await publish_progress(source_id, 40, "Generating embeddings...", "indexing")

        # ── 4. Embed chunks (batched 100) ────────────────────────────────────
        texts = [str(c["text"]) for c in chunks]
        embeddings = await OpenAIAdapter().embed_chunks(texts)

        await publish_progress(source_id, 70, "Indexing in vector store...", "indexing")

        # ── 5. Upsert to Qdrant (tenant-scoped, deterministic IDs) ───────────
        now_iso = datetime.utcnow().isoformat()
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")),
                vector=embeddings[i],
                payload={
                    "tenant_id": tenant_id,
                    "source_id": source_id,
                    "chunk_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")),
                    "profile_id": profile_id,
                    "page_number": 0,
                    "chunk_index": i,
                    "text": chunks[i]["text"],
                    "tags": tags,
                    "created_at": now_iso,
                },
            )
            for i in range(len(chunks))
        ]
        qdrant = QdrantAdapter()
        await qdrant.ensure_collection()
        await qdrant.upsert(points)
        log.info("ingest_text.indexed", point_count=len(points))

        # ── 6. COMPLETED ──────────────────────────────────────────────────────
        await _set_source_completed(source_id, chunk_count=len(chunks))
        await publish_progress(source_id, 100, "Text capture complete!", "completed")

        # ── 6b. Award referrer if this is referee's first upload ───────────────
        try:
            async with async_session_factory() as referral_session:
                await ReferralService().award_referrer_on_first_upload(
                    referral_session,
                    referee_user_id=tenant_id,
                )
        except Exception as referral_exc:
            # Non-fatal: log and continue
            logger.warning(
                "ingest_text.referral_award_failed",
                tenant_id=tenant_id,
                source_id=source_id,
                error=str(referral_exc),
            )

        # ── 7. Enqueue graph extraction ───────────────────────────────────────
        await ctx["redis"].enqueue_job(
            "graph_extraction",
            source_id=source_id,
            tenant_id=tenant_id,
        )
        log.info("ingest_text.graph_extraction_enqueued")

        log.info("ingest_text.completed", chunk_count=len(chunks))
        return {"status": "ok", "source_id": source_id, "chunk_count": len(chunks)}

    except Exception as exc:
        log.error("ingest_text.failed", error=str(exc), exc_info=True)
        try:
            await _set_source_failed(source_id, str(exc))
            await publish_progress(source_id, 0, f"Text capture failed: {exc}", "failed")
        except Exception as inner:
            log.error("ingest_text.cleanup_failed", error=str(inner))
        return {"status": "error", "source_id": source_id, "error": str(exc)}
