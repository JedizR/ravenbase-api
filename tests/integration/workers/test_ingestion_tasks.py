# tests/integration/workers/test_ingestion_tasks.py
"""Integration tests for parse_document ARQ task.

All external adapters (Docling, OpenAI, Storage, Qdrant, Moderation) are mocked.
The PostgreSQL DB uses the real test database (via a patched async_session_factory
that always connects to the local docker postgres).

Note: the local docker postgres schema uses TIMESTAMP WITHOUT TIME ZONE.
ingestion_tasks uses datetime.now(UTC) (tz-aware) for completed_at, which asyncpg
rejects for TZ-naive columns. We patch datetime in ingestion_tasks to return naive
UTC datetimes so the write succeeds.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.source import Source, SourceStatus
from src.models.user import User

_TEST_DB_URL = "postgresql+asyncpg://ravenbase:ravenbase@localhost:5432/ravenbase"
# NullPool: each session.close() fully disconnects — no pooled connections survive
# between tests, preventing "another operation is in progress" errors.
_test_engine = create_async_engine(_TEST_DB_URL, echo=False, poolclass=NullPool)
_test_session_factory = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)


def _naive_now() -> datetime:
    """Return current UTC time without tzinfo (compatible with TIMESTAMP columns)."""
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncSession:
    async with _test_session_factory() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    # Pass explicit naive datetimes — local postgres is TIMESTAMP WITHOUT TIME ZONE
    now = _naive_now()
    user = User(
        id=str(uuid.uuid4()),
        email=f"test-{uuid.uuid4()}@example.com",
        tier="free",
        referral_code=uuid.uuid4().hex[:8].upper(),
        created_at=now,
        updated_at=now,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def pending_source(db_session: AsyncSession, test_user: User) -> Source:
    # Pass explicit naive datetime — local postgres is TIMESTAMP WITHOUT TIME ZONE
    source = Source(
        id=uuid.uuid4(),
        user_id=test_user.id,
        original_filename="test.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        storage_path=f"/{test_user.id}/{uuid.uuid4()}/test.pdf",
        sha256_hash=f"hash-{uuid.uuid4()}",
        file_size_bytes=1024,
        status=SourceStatus.PENDING,
        ingested_at=_naive_now(),
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


def _fake_ctx(redis_mock: MagicMock) -> dict:
    return {"redis": redis_mock}


# ---------------------------------------------------------------------------
# Happy path (AC-1, AC-6, AC-10)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_document_happy_path(
    pending_source: Source,
    test_user: User,
    db_session: AsyncSession,
) -> None:
    """Full happy path: PENDING → PROCESSING → INDEXING → COMPLETED.
    graph_extraction is enqueued. chunk_count saved to Source.
    """
    source_id = str(pending_source.id)
    tenant_id = str(test_user.id)
    fake_chunks = [
        {"text": "Hello world chunk.", "page_number": 0, "chunk_index": 0},
        {"text": "Second chunk of text.", "page_number": 0, "chunk_index": 1},
    ]
    fake_embeddings = [[0.1] * 1536, [0.2] * 1536]
    redis_mock = MagicMock()
    redis_mock.enqueue_job = AsyncMock()

    with (
        patch(
            "src.workers.ingestion_tasks.async_session_factory",
            new=_test_session_factory,
        ),
        patch(
            "src.workers.ingestion_tasks.datetime",
            **{"now.return_value": _naive_now()},
        ),
        patch("src.workers.ingestion_tasks.StorageAdapter") as mock_storage,
        patch("src.workers.ingestion_tasks.ModerationAdapter") as mock_mod,
        patch("src.workers.ingestion_tasks.DoclingAdapter") as mock_docling,
        patch("src.workers.ingestion_tasks.OpenAIAdapter") as mock_embed,
        patch("src.workers.ingestion_tasks.QdrantAdapter") as mock_qdrant,
        patch("src.workers.ingestion_tasks.publish_progress", new_callable=AsyncMock),
    ):
        mock_storage.return_value.download_file = AsyncMock(return_value=b"%PDF fake")
        mock_mod.return_value.check_content = AsyncMock()
        mock_docling.return_value.parse_and_chunk = AsyncMock(return_value=fake_chunks)
        mock_embed.return_value.embed_chunks = AsyncMock(return_value=fake_embeddings)
        mock_qdrant.return_value.upsert = AsyncMock()

        from src.workers.ingestion_tasks import parse_document  # noqa: PLC0415

        result = await parse_document(
            _fake_ctx(redis_mock),
            source_id=source_id,
            tenant_id=tenant_id,
        )

    assert result["status"] == "ok"
    assert result["chunk_count"] == 2

    # Verify DB state: source completed with chunk_count
    await db_session.refresh(pending_source)
    assert pending_source.status == SourceStatus.COMPLETED
    assert pending_source.chunk_count == 2
    assert pending_source.completed_at is not None

    # Verify graph_extraction was enqueued
    redis_mock.enqueue_job.assert_awaited_once_with(
        "graph_extraction",
        source_id=source_id,
        tenant_id=tenant_id,
    )


# ---------------------------------------------------------------------------
# Failure: corrupted PDF (AC-8)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_document_corrupted_pdf_sets_failed_no_retry(
    pending_source: Source,
    test_user: User,
    db_session: AsyncSession,
) -> None:
    """Docling parse failure sets status=FAILED and returns without raising (no retry)."""
    source_id = str(pending_source.id)
    tenant_id = str(test_user.id)
    redis_mock = MagicMock()
    redis_mock.enqueue_job = AsyncMock()

    with (
        patch(
            "src.workers.ingestion_tasks.async_session_factory",
            new=_test_session_factory,
        ),
        patch("src.workers.ingestion_tasks.StorageAdapter") as mock_storage,
        patch("src.workers.ingestion_tasks.ModerationAdapter") as mock_mod,
        patch("src.workers.ingestion_tasks.DoclingAdapter") as mock_docling,
        patch("src.workers.ingestion_tasks.publish_progress", new_callable=AsyncMock),
    ):
        mock_storage.return_value.download_file = AsyncMock(return_value=b"corrupted")
        mock_mod.return_value.check_content = AsyncMock()
        mock_docling.return_value.parse_and_chunk = AsyncMock(
            side_effect=Exception("Docling parse error")
        )

        from src.workers.ingestion_tasks import parse_document  # noqa: PLC0415

        result = await parse_document(
            _fake_ctx(redis_mock),
            source_id=source_id,
            tenant_id=tenant_id,
        )

    # Must return (not raise) so ARQ does not retry
    assert result["status"] == "error"

    await db_session.refresh(pending_source)
    assert pending_source.status == SourceStatus.FAILED
    assert "Docling" in (pending_source.error_message or "")

    # graph_extraction must NOT be enqueued on failure
    redis_mock.enqueue_job.assert_not_awaited()


# ---------------------------------------------------------------------------
# Moderation: hard reject (AC-11)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_document_hard_moderation_reject_deactivates_user(
    pending_source: Source,
    test_user: User,
    db_session: AsyncSession,
) -> None:
    """Hard-reject moderation: source=FAILED + user.is_active=False."""
    source_id = str(pending_source.id)
    tenant_id = str(test_user.id)
    redis_mock = MagicMock()
    redis_mock.enqueue_job = AsyncMock()

    with (
        patch(
            "src.workers.ingestion_tasks.async_session_factory",
            new=_test_session_factory,
        ),
        patch("src.workers.ingestion_tasks.StorageAdapter") as mock_storage,
        patch("src.workers.ingestion_tasks.ModerationAdapter") as mock_mod,
        patch("src.workers.ingestion_tasks.publish_progress", new_callable=AsyncMock),
    ):
        from src.adapters.moderation_adapter import ModerationError  # noqa: PLC0415

        mock_storage.return_value.download_file = AsyncMock(return_value=b"%PDF fake")
        mock_mod.return_value.check_content = AsyncMock(
            side_effect=ModerationError("flagged", hard=True)
        )

        from src.workers.ingestion_tasks import parse_document  # noqa: PLC0415

        result = await parse_document(
            _fake_ctx(redis_mock),
            source_id=source_id,
            tenant_id=tenant_id,
        )

    assert result["status"] == "failed_moderation"

    await db_session.refresh(pending_source)
    assert pending_source.status == SourceStatus.FAILED

    await db_session.refresh(test_user)
    assert test_user.is_active is False


# ---------------------------------------------------------------------------
# Moderation: soft reject (AC-11)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_document_soft_moderation_reject_keeps_user_active(
    pending_source: Source,
    test_user: User,
    db_session: AsyncSession,
) -> None:
    """Soft-reject: source=FAILED but user.is_active stays True."""
    source_id = str(pending_source.id)
    tenant_id = str(test_user.id)
    redis_mock = MagicMock()
    redis_mock.enqueue_job = AsyncMock()

    with (
        patch(
            "src.workers.ingestion_tasks.async_session_factory",
            new=_test_session_factory,
        ),
        patch("src.workers.ingestion_tasks.StorageAdapter") as mock_storage,
        patch("src.workers.ingestion_tasks.ModerationAdapter") as mock_mod,
        patch("src.workers.ingestion_tasks.publish_progress", new_callable=AsyncMock),
    ):
        from src.adapters.moderation_adapter import ModerationError  # noqa: PLC0415

        mock_storage.return_value.download_file = AsyncMock(return_value=b"%PDF fake")
        mock_mod.return_value.check_content = AsyncMock(
            side_effect=ModerationError("flagged", hard=False)
        )

        from src.workers.ingestion_tasks import parse_document  # noqa: PLC0415

        result = await parse_document(
            _fake_ctx(redis_mock),
            source_id=source_id,
            tenant_id=tenant_id,
        )

    assert result["status"] == "failed_moderation"

    await db_session.refresh(pending_source)
    assert pending_source.status == SourceStatus.FAILED

    await db_session.refresh(test_user)
    assert test_user.is_active is True  # user NOT deactivated on soft reject
