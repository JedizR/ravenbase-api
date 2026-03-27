# tests/integration/services/test_rag_retrieval.py
"""Integration tests for RAGService.retrieve().

All external adapters (Qdrant, Neo4j, OpenAI) are mocked.
Tests the full pipeline orchestration end-to-end.
"""

import time
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.schemas.rag import RetrievedChunk
from src.services.rag_service import RAGService


def _make_point(
    chunk_id: str,
    content: str,
    source_id: str | None = None,
    score: float = 0.8,
    profile_id: str | None = None,
    created_at: str = "2025-06-01T00:00:00",
) -> MagicMock:
    p = MagicMock()
    p.id = chunk_id
    p.score = score
    p.payload = {
        "content": content,
        "source_id": str(source_id or uuid.uuid4()),
        "memory_id": None,
        "profile_id": profile_id,
        "created_at": created_at,
        "page_number": None,
    }
    return p


def _make_memory(
    memory_id: str,
    content: str,
    created_at: datetime | None = None,
) -> dict:
    return {
        "memory_id": memory_id,
        "content": content,
        "created_at": created_at or datetime(2025, 6, 1, tzinfo=UTC),
        "confidence": 0.8,
        "source_id": str(uuid.uuid4()),
        "chunk_id": memory_id,
        "profile_id": None,
    }


@pytest.fixture
def mock_openai() -> MagicMock:
    a = MagicMock(spec=OpenAIAdapter)
    a.embed = AsyncMock(return_value=[0.1] * 1536)
    return a


@pytest.fixture
def mock_qdrant() -> MagicMock:
    a = MagicMock(spec=QdrantAdapter)
    a.search = AsyncMock(return_value=[])
    return a


@pytest.fixture
def mock_neo4j() -> MagicMock:
    a = MagicMock(spec=Neo4jAdapter)
    a.find_memories_by_concepts = AsyncMock(return_value=[])
    return a


async def test_full_pipeline_returns_ranked_chunks(mock_openai, mock_qdrant, mock_neo4j) -> None:
    """AC-1, AC-4, AC-5: retrieve() returns ranked, attributed chunks."""
    source_id = str(uuid.uuid4())
    mock_qdrant.search = AsyncMock(
        return_value=[
            _make_point("c1", "Python is great", source_id=source_id, score=0.9),
            _make_point("c2", "FastAPI rocks", source_id=source_id, score=0.7),
        ]
    )
    mock_neo4j.find_memories_by_concepts = AsyncMock(
        return_value=[_make_memory("m1", "Django is also good")]
    )

    svc = RAGService(qdrant=mock_qdrant, neo4j=mock_neo4j, openai=mock_openai)
    results = await svc.retrieve("Python web development", tenant_id="t-1", limit=5)

    assert len(results) == 3
    assert all(isinstance(r, RetrievedChunk) for r in results)
    assert all(r.source_id is not None for r in results)
    assert all(r.final_score > 0.0 for r in results)


async def test_tenant_isolation_qdrant(mock_openai, mock_qdrant, mock_neo4j) -> None:
    """AC-2: tenant_id is always passed to Qdrant search."""
    mock_qdrant.search = AsyncMock(return_value=[])
    mock_neo4j.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant, neo4j=mock_neo4j, openai=mock_openai)
    await svc.retrieve("test", tenant_id="tenant-secure-123")

    qdrant_kwargs = mock_qdrant.search.call_args.kwargs
    assert qdrant_kwargs["tenant_id"] == "tenant-secure-123"


async def test_tenant_isolation_neo4j(mock_openai, mock_qdrant, mock_neo4j) -> None:
    """AC-2: tenant_id is always passed to Neo4j traversal."""
    mock_qdrant.search = AsyncMock(return_value=[])
    mock_neo4j.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant, neo4j=mock_neo4j, openai=mock_openai)
    await svc.retrieve("python fastapi", tenant_id="tenant-secure-123")

    neo4j_kwargs = mock_neo4j.find_memories_by_concepts.call_args.kwargs
    assert neo4j_kwargs["tenant_id"] == "tenant-secure-123"


async def test_profile_id_scoping(mock_openai, mock_qdrant, mock_neo4j) -> None:
    """AC-3: profile_id is passed to both Qdrant and Neo4j."""
    mock_qdrant.search = AsyncMock(return_value=[])
    mock_neo4j.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant, neo4j=mock_neo4j, openai=mock_openai)
    await svc.retrieve("test", tenant_id="t-1", profile_id="prof-xyz")

    neo4j_kwargs = mock_neo4j.find_memories_by_concepts.call_args.kwargs
    assert neo4j_kwargs["profile_id"] == "prof-xyz"

    qdrant_kwargs = mock_qdrant.search.call_args.kwargs
    filters = qdrant_kwargs.get("additional_filters")
    assert filters is not None


async def test_deduplication_of_shared_content(mock_openai, mock_qdrant, mock_neo4j) -> None:
    """AC-5: Same content from Qdrant and Neo4j deduped to one result."""
    shared_content = "Python is great"
    source_id = str(uuid.uuid4())
    mock_qdrant.search = AsyncMock(
        return_value=[_make_point("c1", shared_content, source_id=source_id)]
    )
    mock_neo4j.find_memories_by_concepts = AsyncMock(
        return_value=[_make_memory("m1", shared_content)]
    )

    svc = RAGService(qdrant=mock_qdrant, neo4j=mock_neo4j, openai=mock_openai)
    results = await svc.retrieve("Python", tenant_id="t-1")

    assert len(results) == 1


async def test_empty_prompt_returns_empty(mock_openai, mock_qdrant, mock_neo4j) -> None:
    """AC-6: Empty prompt returns empty list, no errors."""
    svc = RAGService(qdrant=mock_qdrant, neo4j=mock_neo4j, openai=mock_openai)
    results = await svc.retrieve("", tenant_id="t-1")
    assert results == []
    mock_openai.embed.assert_not_called()


async def test_no_relevant_memories_returns_empty(mock_openai, mock_qdrant, mock_neo4j) -> None:
    """AC-6: When both sources return nothing, returns [] without error."""
    mock_qdrant.search = AsyncMock(return_value=[])
    mock_neo4j.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant, neo4j=mock_neo4j, openai=mock_openai)
    results = await svc.retrieve("completely irrelevant prompt xyz", tenant_id="t-1")

    assert results == []


async def test_retrieval_performance_10k_candidates(mock_openai, mock_qdrant, mock_neo4j) -> None:
    """AC-7: Merge + rerank of 10,000 candidates completes in under 3 seconds."""
    big_points = [
        _make_point(
            f"chunk-{i}",
            f"Content about topic number {i} with some extra words to make it realistic",
            score=float(i % 10) / 10.0,
        )
        for i in range(10_000)
    ]
    mock_qdrant.search = AsyncMock(return_value=big_points)
    mock_neo4j.find_memories_by_concepts = AsyncMock(return_value=[])

    svc = RAGService(qdrant=mock_qdrant, neo4j=mock_neo4j, openai=mock_openai)

    start = time.monotonic()
    results = await svc.retrieve("performance test prompt", tenant_id="t-1", limit=10)
    elapsed = time.monotonic() - start

    assert len(results) == 10
    assert elapsed < 3.0, f"Retrieval took {elapsed:.2f}s — must be < 3s"
