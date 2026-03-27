import hashlib
import uuid

import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.adapters.storage_adapter import StorageAdapter
from src.core.config import settings
from src.core.errors import ErrorCode, raise_422, raise_429
from src.models.source import Source, SourceStatus
from src.schemas.ingest import UploadResponse
from src.services.base import BaseService

logger = structlog.get_logger()

FREE_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
PRO_MAX_BYTES = 200 * 1024 * 1024  # 200 MB

ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

RATE_LIMITS = {
    "free": 10,
    "pro": 50,
}


class IngestionService(BaseService):
    def __init__(self, storage: StorageAdapter | None = None) -> None:
        self._storage = storage

    def _get_storage(self) -> StorageAdapter:
        if self._storage is None:
            self._storage = StorageAdapter()
        return self._storage

    def validate_file_type(self, content: bytes) -> str:
        """Detect MIME type from file bytes. Raises 422 if not in allowed set."""
        import magic  # noqa: PLC0415  # lazy: requires system libmagic

        mime = magic.from_buffer(content, mime=True)
        if mime not in ALLOWED_MIMES:
            raise_422(ErrorCode.INVALID_FILE_TYPE, f"Unsupported file type: {mime}")
        return mime

    def validate_file_size(self, size: int, tier: str) -> None:
        """Raises 422 if file exceeds the tier's size limit."""
        limit = PRO_MAX_BYTES if tier == "pro" else FREE_MAX_BYTES
        if size > limit:
            mb = limit // (1024 * 1024)
            raise_422(
                ErrorCode.QUOTA_EXCEEDED,
                f"File exceeds {mb}MB limit for {tier} tier",
            )

    async def check_rate_limit(self, tenant_id: str, tier: str) -> None:
        """Sliding-window rate limit via Redis INCR/EXPIRE.

        Key: rate_limit:{tenant_id}:upload
        Raises 429 QUOTA_EXCEEDED if over the hourly limit.
        """
        import redis.asyncio as aioredis  # noqa: PLC0415

        limit = RATE_LIMITS.get(tier, RATE_LIMITS["free"])
        key = f"rate_limit:{tenant_id}:upload"

        async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, 3600)  # first hit: set 1-hour TTL
            if count > limit:
                raise_429(
                    ErrorCode.QUOTA_EXCEEDED,
                    f"Upload rate limit exceeded ({limit}/hr for {tier} tier)",
                )

    async def handle_upload(
        self,
        *,
        content: bytes,
        filename: str,
        tenant_id: str,
        tier: str,
        arq_pool: object,
        db: AsyncSession,
    ) -> UploadResponse:
        log = logger.bind(tenant_id=tenant_id, filename=filename, tier=tier)
        log.info("ingest.upload.started")

        # 1. Rate limit check
        await self.check_rate_limit(tenant_id, tier)

        # 2. MIME validation
        mime = self.validate_file_type(content)

        # 3. File size check
        self.validate_file_size(len(content), tier)

        # 4. SHA-256 deduplication
        file_hash = hashlib.sha256(content).hexdigest()
        result = await db.exec(
            select(Source).where(
                Source.user_id == tenant_id,
                Source.sha256_hash == file_hash,
            )
        )
        existing = result.first()
        if existing is not None:
            log.info("ingest.upload.duplicate", source_id=str(existing.id))
            return UploadResponse(
                job_id="",
                source_id=existing.id,
                status="duplicate",
                duplicate=True,
            )

        # 5. Generate source_id before storage (used as path component)
        source_id = uuid.uuid4()
        storage_path = f"/{tenant_id}/{source_id}/{filename}"

        # 6. Upload to Supabase Storage
        await self._get_storage().upload_file(content, storage_path)

        # 7. Create Source record in PostgreSQL (status=pending)
        file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        source = Source(
            id=source_id,
            user_id=tenant_id,
            original_filename=filename,
            file_type=file_ext,
            mime_type=mime,
            storage_path=storage_path,
            sha256_hash=file_hash,
            file_size_bytes=len(content),
            status=SourceStatus.PENDING,
        )
        db.add(source)
        await db.commit()

        # 8. Enqueue ARQ job
        job = await arq_pool.enqueue_job(  # type: ignore[union-attr]
            "parse_document",
            source_id=str(source_id),
            tenant_id=tenant_id,
        )
        job_id = job.job_id if job is not None else ""

        log.info("ingest.upload.completed", source_id=str(source_id), job_id=job_id)
        return UploadResponse(
            job_id=job_id,
            source_id=source_id,
            status="queued",
            duplicate=False,
        )

    async def handle_text_ingest(
        self,
        *,
        content: str,
        profile_id: str | None,
        tags: list[str],
        tenant_id: str,
        arq_pool: object,
        db: AsyncSession,
    ) -> UploadResponse:
        log = logger.bind(tenant_id=tenant_id)
        log.info("ingest.text.started", char_count=len(content))

        # 1. Validate content length
        if len(content) > 50_000:
            raise_422(
                ErrorCode.TEXT_TOO_LONG,
                f"Text exceeds 50,000 character limit ({len(content)} chars)",
            )

        # 2. SHA-256 deduplication
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        result = await db.exec(
            select(Source).where(
                Source.user_id == tenant_id,
                Source.sha256_hash == file_hash,
            )
        )
        existing = result.first()
        if existing is not None:
            log.info("ingest.text.duplicate", source_id=str(existing.id))
            return UploadResponse(
                job_id="",
                source_id=existing.id,
                status="duplicate",
                duplicate=True,
            )

        # 3. Create Source record (no file storage — sentinel values)
        source_id = uuid.uuid4()
        source = Source(
            id=source_id,
            user_id=tenant_id,
            profile_id=uuid.UUID(profile_id) if profile_id else None,
            original_filename="direct_input",
            file_type="direct_input",
            mime_type="text/plain",
            storage_path="direct_input",
            sha256_hash=file_hash,
            file_size_bytes=len(content.encode("utf-8")),
            status=SourceStatus.PENDING,
        )
        db.add(source)
        await db.commit()

        # 4. Enqueue ARQ job
        job = await arq_pool.enqueue_job(  # type: ignore[union-attr]
            "ingest_text",
            content=content,
            profile_id=profile_id,
            tags=tags,
            tenant_id=tenant_id,
            source_id=str(source_id),
        )
        job_id = job.job_id if job is not None else ""

        log.info("ingest.text.queued", source_id=str(source_id), job_id=job_id)
        return UploadResponse(
            job_id=job_id,
            source_id=source_id,
            status="queued",
            duplicate=False,
        )

    def cleanup(self) -> None:
        if self._storage:
            self._storage.cleanup()
