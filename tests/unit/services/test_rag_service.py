import uuid
import uuid as _uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.schemas.rag import RetrievedChunk
from src.services.rag_service import (
    RAGService,
    _content_hash,
    extract_concepts,
    merge_and_deduplicate,
    rerank,
)


def test_retrieved_chunk_required_fields() -> None:
    chunk = RetrievedChunk(
        chunk_id="abc123",
        content="User knows Python",
        source_id=uuid.uuid4(),
        final_score=0.85,
        semantic_score=0.9,
        recency_weight=0.7,
    )
    assert chunk.chunk_id == "abc123"
    assert chunk.memory_id is None
    assert chunk.page_number is None


def test_retrieved_chunk_with_all_fields() -> None:
    uid = uuid.uuid4()
    mid = uuid.uuid4()
    chunk = RetrievedChunk(
        chunk_id="abc123",
        content="User knows Python",
        source_id=uid,
        memory_id=mid,
        final_score=0.85,
        semantic_score=0.9,
        recency_weight=0.7,
        page_number=3,
    )
    assert chunk.memory_id == mid
    assert chunk.page_number == 3


async def test_openai_embed_returns_single_vector() -> None:
    adapter = OpenAIAdapter()
    adapter.embed_chunks = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    result = await adapter.embed("hello world")
    adapter.embed_chunks.assert_called_once_with(["hello world"])
    assert result == [0.1, 0.2, 0.3]


async def test_neo4j_find_memories_empty_concepts_returns_empty() -> None:
    adapter = Neo4jAdapter()
    adapter.run_query = AsyncMock(return_value=[])
    result = await adapter.find_memories_by_concepts(concept_names=[], tenant_id="t-1")
    assert result == []
    adapter.run_query.assert_not_called()


async def test_neo4j_find_memories_passes_tenant_id_as_param() -> None:
    adapter = Neo4jAdapter()
    adapter.run_query = AsyncMock(return_value=[])
    await adapter.find_memories_by_concepts(concept_names=["python"], tenant_id="tenant-abc")
    call_kwargs = adapter.run_query.call_args.kwargs
    assert call_kwargs.get("tenant_id") == "tenant-abc"
    # Verify tenant_id not interpolated into query string
    query_str = adapter.run_query.call_args.args[0]
    assert "tenant-abc" not in query_str


# ---------------------------------------------------------------------------
# Part A: extract_concepts tests
# ---------------------------------------------------------------------------


def test_extract_concepts_returns_meaningful_words() -> None:
    concepts = extract_concepts("Tell me about Python and FastAPI development")
    assert "python" in concepts
    assert "fastapi" in concepts
    assert "tell" not in concepts
    assert "and" not in concepts


def test_extract_concepts_empty_prompt_returns_empty() -> None:
    assert extract_concepts("") == []
    assert extract_concepts("   ") == []


def test_extract_concepts_deduplicates() -> None:
    concepts = extract_concepts("Python Python Python is great")
    assert concepts.count("python") == 1


def test_extract_concepts_max_ten() -> None:
    long_prompt = " ".join(f"keyword{i}" for i in range(20))
    concepts = extract_concepts(long_prompt)
    assert len(concepts) <= 10


# ---------------------------------------------------------------------------
# Part B: merge_and_deduplicate tests
# ---------------------------------------------------------------------------


def _make_scored_point(
    chunk_id: str,
    content: str,
    source_id: str | None = None,
    memory_id: str | None = None,
    profile_id: str | None = None,
    score: float = 0.8,
    created_at: str = "2025-01-01T00:00:00",
    page_number: int | None = None,
):
    point = MagicMock()
    point.id = chunk_id
    point.score = score
    point.payload = {
        "content": content,
        "source_id": str(source_id or _uuid.uuid4()),
        "memory_id": memory_id,
        "profile_id": profile_id,
        "created_at": created_at,
        "page_number": page_number,
    }
    return point


def test_merge_deduplicates_by_content_hash() -> None:
    source_id = str(_uuid.uuid4())
    qdrant_pts = [_make_scored_point("c1", "Python is great", source_id=source_id)]
    neo4j_mems = [
        {
            "memory_id": str(_uuid.uuid4()),
            "content": "Python is great",
            "created_at": datetime(2025, 1, 1, tzinfo=UTC),
            "confidence": 0.9,
            "source_id": source_id,
            "chunk_id": "c1",
            "profile_id": None,
        }
    ]
    combined = merge_and_deduplicate(qdrant_pts, neo4j_mems)
    assert len(combined) == 1


def test_merge_keeps_both_when_different_content() -> None:
    qdrant_pts = [_make_scored_point("c1", "Python is great")]
    neo4j_mems = [
        {
            "memory_id": str(_uuid.uuid4()),
            "content": "FastAPI is fast",
            "created_at": datetime(2025, 1, 1, tzinfo=UTC),
            "confidence": 0.9,
            "source_id": str(_uuid.uuid4()),
            "chunk_id": "c2",
            "profile_id": None,
        }
    ]
    combined = merge_and_deduplicate(qdrant_pts, neo4j_mems)
    assert len(combined) == 2


def test_merge_qdrant_result_has_semantic_score() -> None:
    qdrant_pts = [_make_scored_point("c1", "Python is great", score=0.92)]
    combined = merge_and_deduplicate(qdrant_pts, [])
    assert combined[0]["semantic_score"] == 0.92


def test_merge_neo4j_only_result_has_zero_semantic_score() -> None:
    neo4j_mems = [
        {
            "memory_id": str(_uuid.uuid4()),
            "content": "FastAPI is fast",
            "created_at": datetime(2025, 1, 1, tzinfo=UTC),
            "confidence": 0.9,
            "source_id": str(_uuid.uuid4()),
            "chunk_id": "c2",
            "profile_id": None,
        }
    ]
    combined = merge_and_deduplicate([], neo4j_mems)
    assert combined[0]["semantic_score"] == 0.0


# ---------------------------------------------------------------------------
# Part C: rerank tests
# ---------------------------------------------------------------------------


def test_rerank_applies_scoring_formula() -> None:
    now = datetime.now(UTC)
    candidates = [
        {
            "chunk_id": "c1",
            "content": "recent content",
            "source_id": str(_uuid.uuid4()),
            "memory_id": None,
            "semantic_score": 0.9,
            "created_at": now,
            "profile_id": "prof-1",
            "page_number": None,
            "content_hash": _content_hash("recent content"),
        },
        {
            "chunk_id": "c2",
            "content": "old content",
            "source_id": str(_uuid.uuid4()),
            "memory_id": None,
            "semantic_score": 0.9,
            "created_at": datetime(2020, 1, 1, tzinfo=UTC),
            "profile_id": None,
            "page_number": None,
            "content_hash": _content_hash("old content"),
        },
    ]
    ranked = rerank(candidates)
    assert ranked[0].chunk_id == "c1"
    assert ranked[1].chunk_id == "c2"
    assert 0.0 <= ranked[0].final_score <= 1.0


def test_rerank_returns_retrieved_chunk_instances() -> None:
    candidates = [
        {
            "chunk_id": "c1",
            "content": "test",
            "source_id": str(_uuid.uuid4()),
            "memory_id": None,
            "semantic_score": 0.5,
            "created_at": datetime.now(UTC),
            "profile_id": None,
            "page_number": 2,
            "content_hash": _content_hash("test"),
        }
    ]
    ranked = rerank(candidates)
    assert len(ranked) == 1
    assert isinstance(ranked[0], RetrievedChunk)
    assert ranked[0].page_number == 2


def test_rerank_empty_input_returns_empty() -> None:
    assert rerank([]) == []


# ---------------------------------------------------------------------------
# Part D: RAGService skeleton tests
# ---------------------------------------------------------------------------


def test_rag_service_instantiates_with_injected_adapters() -> None:
    qdrant = MagicMock(spec=QdrantAdapter)
    neo4j = MagicMock(spec=Neo4jAdapter)
    openai = MagicMock(spec=OpenAIAdapter)
    svc = RAGService(qdrant=qdrant, neo4j=neo4j, openai=openai)
    assert svc is not None


def test_rag_service_cleanup_clears_adapters() -> None:
    qdrant = MagicMock(spec=QdrantAdapter)
    svc = RAGService(qdrant=qdrant)
    svc.cleanup()
    qdrant.cleanup.assert_called_once()


# ---------------------------------------------------------------------------
# Part E: retrieve() pipeline tests
# ---------------------------------------------------------------------------


# Local fixtures for retrieve() pipeline tests
@pytest.fixture
def mock_neo4j_svc():
    a = MagicMock(spec=Neo4jAdapter)
    a.find_memories_by_concepts = AsyncMock(return_value=[])
    return a


@pytest.fixture
def mock_qdrant_svc():
    a = MagicMock(spec=QdrantAdapter)
    a.search = AsyncMock(return_value=[])
    a.upsert = AsyncMock()
    a.delete_by_filter = AsyncMock()
    a.count = AsyncMock(return_value=0)
    a.verify_connectivity = AsyncMock(return_value=True)
    return a


async def test_retrieve_calls_all_three_phases(mock_qdrant_svc, mock_neo4j_svc) -> None:
    mock_openai = MagicMock(spec=OpenAIAdapter)
    mock_openai.embed = AsyncMock(return_value=[0.1] * 1536)

    source_id = str(uuid.uuid4())
    mock_point = _make_scored_point("c1", "Python is great", source_id=source_id, score=0.85)
    mock_qdrant_svc.search = AsyncMock(return_value=[mock_point])
    mock_neo4j_svc.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant_svc, neo4j=mock_neo4j_svc, openai=mock_openai)
    results = await svc.retrieve("Python development", tenant_id="t-1")

    mock_openai.embed.assert_called_once_with("Python development")
    mock_qdrant_svc.search.assert_called_once()
    call_kwargs = mock_qdrant_svc.search.call_args.kwargs
    assert call_kwargs["tenant_id"] == "t-1"
    assert len(results) == 1


async def test_retrieve_qdrant_search_includes_tenant_id(mock_qdrant_svc, mock_neo4j_svc) -> None:
    mock_openai = MagicMock(spec=OpenAIAdapter)
    mock_openai.embed = AsyncMock(return_value=[0.1] * 1536)
    mock_qdrant_svc.search = AsyncMock(return_value=[])
    mock_neo4j_svc.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant_svc, neo4j=mock_neo4j_svc, openai=mock_openai)
    await svc.retrieve("test prompt", tenant_id="tenant-xyz")

    search_kwargs = mock_qdrant_svc.search.call_args.kwargs
    assert search_kwargs["tenant_id"] == "tenant-xyz"


async def test_retrieve_neo4j_includes_tenant_id(mock_qdrant_svc, mock_neo4j_svc) -> None:
    mock_openai = MagicMock(spec=OpenAIAdapter)
    mock_openai.embed = AsyncMock(return_value=[0.1] * 1536)
    mock_qdrant_svc.search = AsyncMock(return_value=[])
    mock_neo4j_svc.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant_svc, neo4j=mock_neo4j_svc, openai=mock_openai)
    await svc.retrieve("python fastapi", tenant_id="tenant-xyz")

    neo4j_kwargs = mock_neo4j_svc.find_memories_by_concepts.call_args.kwargs
    assert neo4j_kwargs["tenant_id"] == "tenant-xyz"


async def test_retrieve_empty_prompt_returns_empty(mock_qdrant_svc, mock_neo4j_svc) -> None:
    mock_openai = MagicMock(spec=OpenAIAdapter)
    mock_openai.embed = AsyncMock(return_value=[0.1] * 1536)

    svc = RAGService(qdrant=mock_qdrant_svc, neo4j=mock_neo4j_svc, openai=mock_openai)
    results = await svc.retrieve("", tenant_id="t-1")

    assert results == []
    mock_openai.embed.assert_not_called()


async def test_retrieve_respects_limit(mock_qdrant_svc, mock_neo4j_svc) -> None:
    mock_openai = MagicMock(spec=OpenAIAdapter)
    mock_openai.embed = AsyncMock(return_value=[0.1] * 1536)
    points = [
        _make_scored_point(f"c{i}", f"Content chunk {i}", score=float(i) / 10) for i in range(5)
    ]
    mock_qdrant_svc.search = AsyncMock(return_value=points)
    mock_neo4j_svc.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant_svc, neo4j=mock_neo4j_svc, openai=mock_openai)
    results = await svc.retrieve("test", tenant_id="t-1", limit=3)

    assert len(results) == 3


async def test_retrieve_with_profile_id_passes_to_qdrant(mock_qdrant_svc, mock_neo4j_svc) -> None:
    mock_openai = MagicMock(spec=OpenAIAdapter)
    mock_openai.embed = AsyncMock(return_value=[0.1] * 1536)
    mock_qdrant_svc.search = AsyncMock(return_value=[])
    mock_neo4j_svc.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant_svc, neo4j=mock_neo4j_svc, openai=mock_openai)
    await svc.retrieve("test", tenant_id="t-1", profile_id="prof-abc")

    search_kwargs = mock_qdrant_svc.search.call_args.kwargs
    filters = search_kwargs.get("additional_filters")
    assert filters is not None
    must_conditions = filters.must
    assert any(getattr(cond, "key", None) == "profile_id" for cond in (must_conditions or []))
