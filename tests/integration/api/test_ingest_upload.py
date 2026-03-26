# tests/integration/api/test_ingest_upload.py
"""
Integration tests for POST /v1/ingest/upload.

All external dependencies (DB, Supabase Storage, Redis, ARQ) are mocked so
this suite runs without a live database or network.

Run with: uv run pytest tests/integration/api/test_ingest_upload.py -v
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.api.main import app
from src.core.errors import ErrorCode
from src.models.source import Source, SourceStatus
from src.services.ingestion_service import IngestionService

# Minimal payloads – content doesn't matter since magic.from_buffer is mocked
PDF_BYTES = b"%PDF-1.4 fake pdf content for testing"
TEXT_BYTES = b"Hello, plain text content for testing."
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

TEST_TENANT_ID = str(uuid.uuid4())
KNOWN_SOURCE_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _make_mock_db(existing_source: Source | None = None) -> AsyncMock:
    """Build a mock AsyncSession that returns `existing_source` on dedup queries."""
    mock_result = MagicMock()
    mock_result.first.return_value = existing_source

    mock_db = AsyncMock()
    mock_db.exec = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    return mock_db


async def _mock_db_gen(mock_db: AsyncMock):
    yield mock_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def ingest_client(mocker):
    """Client with mocked ARQ pool, storage, rate limiter, auth, and DB (no duplicates).

    ASGITransport does not trigger the ASGI lifespan, so app.state.arq_pool is set
    directly rather than through the lifespan create_pool call.
    """
    mock_job = MagicMock()
    mock_job.job_id = "test-job-abc123"
    mock_pool = AsyncMock()
    mock_pool.enqueue_job = AsyncMock(return_value=mock_job)
    # Set app.state directly — lifespan does not run with ASGITransport
    app.state.arq_pool = mock_pool

    mocker.patch(
        "src.adapters.storage_adapter.StorageAdapter.upload_file",
        new=AsyncMock(return_value=f"/{TEST_TENANT_ID}/source-id/file.pdf"),
    )
    mocker.patch(
        "src.services.ingestion_service.IngestionService.check_rate_limit",
        new=AsyncMock(),
    )

    mock_db = _make_mock_db(existing_source=None)

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
        "tier": "free",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    del app.state.arq_pool
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user, None)


@pytest.fixture
async def ingest_client_with_duplicate(mocker):
    """Client pre-configured with an existing Source so dedup triggers."""
    mock_pool = AsyncMock()
    app.state.arq_pool = mock_pool

    mocker.patch(
        "src.adapters.storage_adapter.StorageAdapter.upload_file",
        new=AsyncMock(return_value=f"/{TEST_TENANT_ID}/source-id/file.pdf"),
    )
    mocker.patch(
        "src.services.ingestion_service.IngestionService.check_rate_limit",
        new=AsyncMock(),
    )

    existing = Source(
        id=KNOWN_SOURCE_ID,
        user_id=uuid.UUID(TEST_TENANT_ID),
        original_filename="dup.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        storage_path=f"/{TEST_TENANT_ID}/{KNOWN_SOURCE_ID}/dup.pdf",
        sha256_hash="aabbcc",
        file_size_bytes=100,
        status=SourceStatus.PENDING,
    )
    mock_db = _make_mock_db(existing_source=existing)

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
        "tier": "free",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    del app.state.arq_pool
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(require_user, None)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_valid_pdf_returns_202_queued(ingest_client: AsyncClient, mocker) -> None:
    """Valid PDF → 202, status=queued, duplicate=False."""
    mocker.patch.object(IngestionService, "validate_file_type", return_value="application/pdf")

    response = await ingest_client.post(
        "/v1/ingest/upload",
        files={"file": ("test.pdf", PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["duplicate"] is False
    assert data["job_id"] == "test-job-abc123"
    assert uuid.UUID(data["source_id"])


@pytest.mark.asyncio
async def test_upload_plain_text_returns_202_queued(ingest_client: AsyncClient, mocker) -> None:
    """text/plain upload → 202, status=queued."""
    mocker.patch.object(IngestionService, "validate_file_type", return_value="text/plain")

    response = await ingest_client.post(
        "/v1/ingest/upload",
        files={"file": ("notes.txt", TEXT_BYTES, "text/plain")},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_upload_duplicate_returns_existing_source_id(
    ingest_client_with_duplicate: AsyncClient, mocker
) -> None:
    """Uploading a file whose SHA-256 is already in DB → 202, duplicate=True, same source_id."""
    mocker.patch.object(IngestionService, "validate_file_type", return_value="application/pdf")

    response = await ingest_client_with_duplicate.post(
        "/v1/ingest/upload",
        files={"file": ("dup.pdf", PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "duplicate"
    assert data["duplicate"] is True
    assert uuid.UUID(data["source_id"]) == KNOWN_SOURCE_ID
    assert data["job_id"] == ""


@pytest.mark.asyncio
async def test_upload_invalid_mime_returns_422(ingest_client: AsyncClient, mocker) -> None:
    """Unsupported file type → 422 INVALID_FILE_TYPE."""
    mocker.patch.object(
        IngestionService,
        "validate_file_type",
        side_effect=HTTPException(
            status_code=422,
            detail={"code": ErrorCode.INVALID_FILE_TYPE, "message": "Unsupported file type"},
        ),
    )

    response = await ingest_client.post(
        "/v1/ingest/upload",
        files={"file": ("image.png", PNG_BYTES, "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_oversized_file_returns_422(ingest_client: AsyncClient, mocker) -> None:
    """File exceeding free-tier 50 MB limit → 422 QUOTA_EXCEEDED."""
    mocker.patch.object(IngestionService, "validate_file_type", return_value="application/pdf")
    oversized = b"%PDF-1.4 " + b"x" * (51 * 1024 * 1024)

    response = await ingest_client.post(
        "/v1/ingest/upload",
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "QUOTA_EXCEEDED"


@pytest.mark.asyncio
async def test_upload_rate_limited_returns_429(ingest_client: AsyncClient, mocker) -> None:
    """Rate limit exceeded → 429 QUOTA_EXCEEDED."""
    mocker.patch.object(
        IngestionService,
        "check_rate_limit",
        side_effect=HTTPException(
            status_code=429,
            detail={"code": ErrorCode.QUOTA_EXCEEDED, "message": "Rate limit exceeded"},
        ),
    )
    mocker.patch.object(IngestionService, "validate_file_type", return_value="application/pdf")

    response = await ingest_client.post(
        "/v1/ingest/upload",
        files={"file": ("test.pdf", PDF_BYTES, "application/pdf")},
    )

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "QUOTA_EXCEEDED"
