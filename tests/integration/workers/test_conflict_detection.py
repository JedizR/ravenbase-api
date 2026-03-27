# tests/integration/workers/test_conflict_detection.py
"""Integration tests for ConflictService and the scan_for_conflicts ARQ task.

All external adapters (Qdrant, Neo4j, LLMRouter, Redis) are mocked.
The PostgreSQL DB uses the real test database (local docker postgres).
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.conflict import Conflict, ConflictStatus
from src.models.source import Source, SourceAuthorityWeight, SourceStatus
from src.models.user import User

_TEST_DB_URL = "postgresql+asyncpg://ravenbase:ravenbase@localhost:5432/ravenbase"
_test_engine = create_async_engine(_TEST_DB_URL, echo=False, poolclass=NullPool)
_test_session_factory = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)


def _naive_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _mock_conflict_datetime():
    """Patch Conflict.created_at default_factory to return TIMESTAMP-compatible naive datetime.

    Local postgres uses TIMESTAMP WITHOUT TIME ZONE; datetime.now(UTC) (tz-aware) is rejected.
    Matches the pattern used in test_ingestion_tasks.py.
    """
    mock_dt = MagicMock()
    mock_dt.now.return_value = _naive_now()
    return patch("src.models.conflict.datetime", mock_dt)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session() -> AsyncSession:
    async with _test_session_factory() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
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
async def test_user_b(db_session: AsyncSession) -> User:
    """Second user for tenant isolation tests."""
    now = _naive_now()
    user = User(
        id=str(uuid.uuid4()),
        email=f"test-b-{uuid.uuid4()}@example.com",
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
async def challenger_source(db_session: AsyncSession, test_user: User) -> Source:
    """The newly ingested source (challenger)."""
    source = Source(
        id=uuid.uuid4(),
        user_id=test_user.id,
        original_filename="new_doc.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        storage_path=f"/{test_user.id}/{uuid.uuid4()}/new_doc.pdf",
        sha256_hash=f"hash-new-{uuid.uuid4()}",
        file_size_bytes=512,
        status=SourceStatus.COMPLETED,
        ingested_at=_naive_now(),
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


@pytest.fixture
async def incumbent_source(db_session: AsyncSession, test_user: User) -> Source:
    """An older existing source (incumbent)."""
    source = Source(
        id=uuid.uuid4(),
        user_id=test_user.id,
        original_filename="old_doc.txt",
        file_type="txt",
        mime_type="text/plain",
        storage_path=f"/{test_user.id}/{uuid.uuid4()}/old_doc.txt",
        sha256_hash=f"hash-old-{uuid.uuid4()}",
        file_size_bytes=256,
        status=SourceStatus.COMPLETED,
        ingested_at=_naive_now(),
    )
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source


def _make_mock_qdrant(
    challenger_source_id: str,
    tenant_id: str,
    incumbent_source_id: str,
    incumbent_chunk_id: str = "incumbent-chunk-1",
    incumbent_text: str = "I am a senior Python developer.",
    challenger_chunk_id: str = "challenger-chunk-1",
    challenger_text: str = "I am a junior Python developer.",
    search_results: list | None = None,
) -> MagicMock:
    """Return a mock QdrantAdapter with pre-configured return values."""
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    mock_qdrant = MagicMock(spec=QdrantAdapter)

    # scroll_by_source_with_vectors returns list[(point_id, vector, payload)]
    mock_qdrant.scroll_by_source_with_vectors = AsyncMock(
        return_value=[
            (
                challenger_chunk_id,
                [0.1] * 1536,
                {
                    "chunk_id": challenger_chunk_id,
                    "text": challenger_text,
                    "source_id": challenger_source_id,
                    "tenant_id": tenant_id,
                },
            )
        ]
    )

    # Default: one high-similarity hit from the incumbent source
    if search_results is None:
        hit = MagicMock()
        hit.payload = {
            "chunk_id": incumbent_chunk_id,
            "text": incumbent_text,
            "source_id": incumbent_source_id,
            "tenant_id": tenant_id,
        }
        search_results = [hit]

    mock_qdrant.search = AsyncMock(return_value=search_results)
    return mock_qdrant


def _make_mock_llm(classification: str, confidence: float = 0.9) -> MagicMock:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    mock_llm = MagicMock(spec=LLMRouter)
    mock_llm.complete = AsyncMock(
        return_value=json.dumps(
            {
                "classification": classification,
                "confidence": confidence,
                "reasoning": "test reasoning",
            }
        )
    )
    return mock_llm


def _make_mock_neo4j() -> MagicMock:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    mock_neo4j = MagicMock(spec=Neo4jAdapter)
    mock_neo4j.write_relationships = AsyncMock()
    return mock_neo4j


def _mock_redis_ctx():
    """Context managers to silence Redis during non-Redis tests."""
    mock_r = MagicMock()
    mock_r.publish = AsyncMock()
    mock_r.aclose = AsyncMock()
    return patch("redis.asyncio.from_url", new=AsyncMock(return_value=mock_r))


# ---------------------------------------------------------------------------
# AC-5, AC-6: CONTRADICTION → Conflict record + CONTRADICTS edge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_for_conflicts_creates_conflict_for_contradiction(
    db_session: AsyncSession,
    test_user: User,
    challenger_source: Source,
    incumbent_source: Source,
) -> None:
    """CONTRADICTION classification creates Conflict record with status=PENDING."""
    from sqlmodel import select  # noqa: PLC0415

    from src.services.conflict_service import ConflictService  # noqa: PLC0415

    tenant_id = str(test_user.id)
    mock_qdrant = _make_mock_qdrant(
        challenger_source_id=str(challenger_source.id),
        tenant_id=tenant_id,
        incumbent_source_id=str(incumbent_source.id),
    )
    mock_llm = _make_mock_llm("CONTRADICTION")
    mock_neo4j = _make_mock_neo4j()

    service = ConflictService(qdrant=mock_qdrant, neo4j=mock_neo4j, llm_router=mock_llm)

    with (
        patch(
            "src.services.conflict_service.async_session_factory",
            new=_test_session_factory,
        ),
        _mock_redis_ctx(),
        _mock_conflict_datetime(),
    ):
        result = await service.scan_and_create_conflicts(
            source_id=str(challenger_source.id),
            tenant_id=tenant_id,
        )

    assert result["conflict_count"] == 1
    assert result["skipped_count"] == 0

    # Verify Conflict record in DB
    stmt = select(Conflict).where(Conflict.user_id == test_user.id)
    conflicts = (await db_session.exec(stmt)).all()
    assert len(conflicts) == 1
    assert conflicts[0].status == ConflictStatus.PENDING
    assert conflicts[0].ai_classification == "CONTRADICTION"
    assert conflicts[0].confidence_score == 0.9
    assert conflicts[0].challenger_source_id == challenger_source.id

    # Verify CONTRADICTS edge written to Neo4j
    mock_neo4j.write_relationships.assert_awaited_once()
    call_kwargs = mock_neo4j.write_relationships.call_args.kwargs
    assert call_kwargs["rel_type"] == "CONTRADICTS"
    assert call_kwargs["tenant_id"] == tenant_id


# ---------------------------------------------------------------------------
# AC-10: COMPLEMENT → TEMPORAL_LINK edge only, no Conflict record
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_for_conflicts_writes_temporal_link_for_complement(
    db_session: AsyncSession,
    test_user: User,
    challenger_source: Source,
    incumbent_source: Source,
) -> None:
    """COMPLEMENT classification writes TEMPORAL_LINK edge but no Conflict DB record."""
    from sqlmodel import select  # noqa: PLC0415

    from src.services.conflict_service import ConflictService  # noqa: PLC0415

    tenant_id = str(test_user.id)
    mock_qdrant = _make_mock_qdrant(
        challenger_source_id=str(challenger_source.id),
        tenant_id=tenant_id,
        incumbent_source_id=str(incumbent_source.id),
    )
    mock_llm = _make_mock_llm("COMPLEMENT")
    mock_neo4j = _make_mock_neo4j()

    service = ConflictService(qdrant=mock_qdrant, neo4j=mock_neo4j, llm_router=mock_llm)

    with patch(
        "src.services.conflict_service.async_session_factory",
        new=_test_session_factory,
    ):
        result = await service.scan_and_create_conflicts(
            source_id=str(challenger_source.id),
            tenant_id=tenant_id,
        )

    assert result["conflict_count"] == 0
    assert result["skipped_count"] == 1

    # No Conflict records
    stmt = select(Conflict).where(Conflict.user_id == test_user.id)
    conflicts = (await db_session.exec(stmt)).all()
    assert len(conflicts) == 0

    # TEMPORAL_LINK edge written
    mock_neo4j.write_relationships.assert_awaited_once()
    call_kwargs = mock_neo4j.write_relationships.call_args.kwargs
    assert call_kwargs["rel_type"] == "TEMPORAL_LINK"
    assert call_kwargs["tenant_id"] == tenant_id


# ---------------------------------------------------------------------------
# AC-7: Auto-resolution when challenger authority delta >= 3
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_for_conflicts_auto_resolves_when_authority_delta_gte_3(
    db_session: AsyncSession,
    test_user: User,
    challenger_source: Source,
    incumbent_source: Source,
) -> None:
    """Challenger authority 6, incumbent 3 → delta=3 → conflict auto-resolved."""
    from sqlmodel import select  # noqa: PLC0415

    from src.services.conflict_service import ConflictService  # noqa: PLC0415

    tenant_id = str(test_user.id)

    # Seed authority weights: incumbent (txt)=3, challenger (pdf)=6
    db_session.add(
        SourceAuthorityWeight(
            user_id=test_user.id,
            source_type=incumbent_source.file_type,
            weight=3,
        )
    )
    db_session.add(
        SourceAuthorityWeight(
            user_id=test_user.id,
            source_type=challenger_source.file_type,
            weight=6,
        )
    )
    await db_session.commit()

    mock_qdrant = _make_mock_qdrant(
        challenger_source_id=str(challenger_source.id),
        tenant_id=tenant_id,
        incumbent_source_id=str(incumbent_source.id),
    )
    mock_llm = _make_mock_llm("CONTRADICTION")
    mock_neo4j = _make_mock_neo4j()

    service = ConflictService(qdrant=mock_qdrant, neo4j=mock_neo4j, llm_router=mock_llm)

    with (
        patch(
            "src.services.conflict_service.async_session_factory",
            new=_test_session_factory,
        ),
        _mock_redis_ctx(),
        _mock_conflict_datetime(),
    ):
        result = await service.scan_and_create_conflicts(
            source_id=str(challenger_source.id),
            tenant_id=tenant_id,
        )

    assert result["auto_resolved_count"] == 1
    assert result["conflict_count"] == 1

    # Verify AUTO_RESOLVED in DB
    stmt = select(Conflict).where(Conflict.user_id == test_user.id)
    conflicts = (await db_session.exec(stmt)).all()
    assert len(conflicts) == 1
    assert conflicts[0].status == ConflictStatus.AUTO_RESOLVED
    assert "Auto-resolved" in (conflicts[0].resolution_note or "")


# ---------------------------------------------------------------------------
# AC-9: Maximum 5 conflicts per batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_for_conflicts_caps_at_5_conflicts(
    db_session: AsyncSession,
    test_user: User,
    challenger_source: Source,
    incumbent_source: Source,
) -> None:
    """Even if Qdrant returns many candidates, only 5 LLM calls and <=5 Conflict records."""
    from sqlmodel import select  # noqa: PLC0415

    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415
    from src.services.conflict_service import ConflictService  # noqa: PLC0415

    tenant_id = str(test_user.id)

    # 10 chunks in the new source, each matching 1 unique incumbent chunk
    chunks_with_vectors = []
    search_hits_per_chunk = []
    for i in range(10):
        chunk_id = f"challenger-chunk-{i}"
        inc_chunk_id = f"incumbent-chunk-{i}"
        chunks_with_vectors.append(
            (
                chunk_id,
                [0.1 * (i + 1)] * 1536,
                {
                    "chunk_id": chunk_id,
                    "text": f"challenger text {i}",
                    "source_id": str(challenger_source.id),
                    "tenant_id": tenant_id,
                },
            )
        )
        hit = MagicMock()
        hit.payload = {
            "chunk_id": inc_chunk_id,
            "text": f"incumbent text {i}",
            "source_id": str(incumbent_source.id),
            "tenant_id": tenant_id,
        }
        search_hits_per_chunk.append([hit])

    mock_qdrant = MagicMock(spec=QdrantAdapter)
    mock_qdrant.scroll_by_source_with_vectors = AsyncMock(return_value=chunks_with_vectors)
    mock_qdrant.search = AsyncMock(side_effect=search_hits_per_chunk)

    mock_llm = _make_mock_llm("CONTRADICTION")
    mock_neo4j = _make_mock_neo4j()

    service = ConflictService(qdrant=mock_qdrant, neo4j=mock_neo4j, llm_router=mock_llm)

    with (
        patch(
            "src.services.conflict_service.async_session_factory",
            new=_test_session_factory,
        ),
        _mock_redis_ctx(),
        _mock_conflict_datetime(),
    ):
        result = await service.scan_and_create_conflicts(
            source_id=str(challenger_source.id),
            tenant_id=tenant_id,
        )

    # LLM called at most 5 times (slice before LLM loop)
    assert mock_llm.complete.await_count <= 5

    # At most 5 Conflict records
    assert result["conflict_count"] <= 5

    stmt = select(Conflict).where(Conflict.user_id == test_user.id)
    conflicts = (await db_session.exec(stmt)).all()
    assert len(conflicts) <= 5


# ---------------------------------------------------------------------------
# AC-8: Redis pub/sub notification after DB commit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_for_conflicts_publishes_redis_notification(
    test_user: User,
    challenger_source: Source,
    incumbent_source: Source,
) -> None:
    """Conflict created → Redis publishes to conflict:new:{tenant_id} after commit."""
    from src.services.conflict_service import ConflictService  # noqa: PLC0415

    tenant_id = str(test_user.id)
    mock_qdrant = _make_mock_qdrant(
        challenger_source_id=str(challenger_source.id),
        tenant_id=tenant_id,
        incumbent_source_id=str(incumbent_source.id),
    )
    mock_llm = _make_mock_llm("CONTRADICTION")
    mock_neo4j = _make_mock_neo4j()

    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock()
    mock_redis.aclose = AsyncMock()

    service = ConflictService(qdrant=mock_qdrant, neo4j=mock_neo4j, llm_router=mock_llm)

    with (
        patch(
            "src.services.conflict_service.async_session_factory",
            new=_test_session_factory,
        ),
        patch("redis.asyncio.from_url", new=AsyncMock(return_value=mock_redis)),
        _mock_conflict_datetime(),
    ):
        await service.scan_and_create_conflicts(
            source_id=str(challenger_source.id),
            tenant_id=tenant_id,
        )

    expected_channel = f"conflict:new:{tenant_id}"
    mock_redis.publish.assert_awaited_once()
    actual_channel = mock_redis.publish.call_args[0][0]
    assert actual_channel == expected_channel


# ---------------------------------------------------------------------------
# MANDATORY: Tenant isolation (from story critical test requirement)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_conflict_detection_tenant_isolation(
    db_session: AsyncSession,
    test_user: User,
    test_user_b: User,
    challenger_source: Source,
    incumbent_source: Source,
) -> None:
    """User A's scan must NEVER pass User B's tenant_id to Qdrant search.

    Seed identical chunk text for both users; run scan for user A only.
    Assert every search() call used user A's tenant_id.
    Assert user B's tenant_id never appeared in any search call.
    """
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415
    from src.services.conflict_service import ConflictService  # noqa: PLC0415

    tenant_id_a = str(test_user.id)
    tenant_id_b = str(test_user_b.id)

    # Track all search() calls made
    search_call_tenant_ids: list[str] = []

    async def capturing_search(query_vector, tenant_id, **kwargs):  # type: ignore[no-untyped-def]
        search_call_tenant_ids.append(tenant_id)
        return []  # No hits — we just want to verify isolation

    mock_qdrant = MagicMock(spec=QdrantAdapter)
    mock_qdrant.scroll_by_source_with_vectors = AsyncMock(
        return_value=[
            (
                "chunk-a-1",
                [0.5] * 1536,
                {
                    "chunk_id": "chunk-a-1",
                    "text": "I am a Python developer",
                    "source_id": str(challenger_source.id),
                    "tenant_id": tenant_id_a,
                },
            )
        ]
    )
    mock_qdrant.search = AsyncMock(side_effect=capturing_search)

    service = ConflictService(
        qdrant=mock_qdrant,
        neo4j=_make_mock_neo4j(),
        llm_router=_make_mock_llm("COMPLEMENT"),
    )

    with patch(
        "src.services.conflict_service.async_session_factory",
        new=_test_session_factory,
    ):
        await service.scan_and_create_conflicts(
            source_id=str(challenger_source.id),
            tenant_id=tenant_id_a,
        )

    # At least one search was made
    assert len(search_call_tenant_ids) > 0, "search() was never called"

    # Every search call used USER A's tenant_id
    for tid in search_call_tenant_ids:
        assert tid == tenant_id_a, (
            f"search() called with tenant_id={tid!r} but expected {tenant_id_a!r}"
        )

    # USER B's tenant_id never appeared in any search call
    assert tenant_id_b not in search_call_tenant_ids, (
        "USER B's tenant_id leaked into a search call — tenant isolation breach!"
    )


# ---------------------------------------------------------------------------
# DUPLICATE classification: no Conflict record, no Neo4j edge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_for_conflicts_skips_duplicate_classification(
    db_session: AsyncSession,
    test_user: User,
    challenger_source: Source,
    incumbent_source: Source,
) -> None:
    """DUPLICATE classification: skip silently — no DB record, no Neo4j edge."""
    from sqlmodel import select  # noqa: PLC0415

    from src.services.conflict_service import ConflictService  # noqa: PLC0415

    tenant_id = str(test_user.id)
    mock_qdrant = _make_mock_qdrant(
        challenger_source_id=str(challenger_source.id),
        tenant_id=tenant_id,
        incumbent_source_id=str(incumbent_source.id),
    )
    mock_llm = _make_mock_llm("DUPLICATE")
    mock_neo4j = _make_mock_neo4j()

    service = ConflictService(qdrant=mock_qdrant, neo4j=mock_neo4j, llm_router=mock_llm)

    with patch(
        "src.services.conflict_service.async_session_factory",
        new=_test_session_factory,
    ):
        result = await service.scan_and_create_conflicts(
            source_id=str(challenger_source.id),
            tenant_id=tenant_id,
        )

    assert result["conflict_count"] == 0
    assert result["skipped_count"] == 1

    # No Conflict records
    stmt = select(Conflict).where(Conflict.user_id == test_user.id)
    conflicts = (await db_session.exec(stmt)).all()
    assert len(conflicts) == 0

    # No Neo4j edges
    mock_neo4j.write_relationships.assert_not_awaited()


# ---------------------------------------------------------------------------
# Task wrapper: scan_for_conflicts ARQ task
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_for_conflicts_task_returns_ok_on_success() -> None:
    """Task wrapper passes source_id/tenant_id to service, returns ok dict."""
    from src.workers.conflict_tasks import scan_for_conflicts  # noqa: PLC0415

    mock_stats = {"conflict_count": 1, "skipped_count": 0, "auto_resolved_count": 0}

    with patch("src.workers.conflict_tasks.ConflictService") as mock_svc_cls:
        mock_svc_cls.return_value.scan_and_create_conflicts = AsyncMock(return_value=mock_stats)
        result = await scan_for_conflicts(
            {},
            source_id="src-123",
            tenant_id="tenant-abc",
        )

    assert result["status"] == "ok"
    assert result["conflict_count"] == 1
    assert result["source_id"] == "src-123"
    mock_svc_cls.return_value.scan_and_create_conflicts.assert_awaited_once_with(
        source_id="src-123",
        tenant_id="tenant-abc",
    )


@pytest.mark.asyncio
async def test_scan_for_conflicts_task_returns_error_without_raising() -> None:
    """Task wrapper catches exceptions and returns error dict (no retry)."""
    from src.workers.conflict_tasks import scan_for_conflicts  # noqa: PLC0415

    with patch("src.workers.conflict_tasks.ConflictService") as mock_svc_cls:
        mock_svc_cls.return_value.scan_and_create_conflicts = AsyncMock(
            side_effect=RuntimeError("Qdrant unreachable")
        )
        result = await scan_for_conflicts(
            {},
            source_id="src-456",
            tenant_id="tenant-xyz",
        )

    assert result["status"] == "error"
    assert "Qdrant unreachable" in result["error"]
    assert result["source_id"] == "src-456"
