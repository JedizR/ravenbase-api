import json
from unittest.mock import AsyncMock, MagicMock

import pytest


def _llm_response(
    entities: list | None = None,
    memories: list | None = None,
    relationships: list | None = None,
) -> str:
    return json.dumps(
        {
            "entities": [{"name": "Python", "type": "skill", "confidence": 0.9}]
            if entities is None
            else entities,
            "memories": [{"content": "User knows Python", "confidence": 0.8}]
            if memories is None
            else memories,
            "relationships": [] if relationships is None else relationships,
        }
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    r = MagicMock(spec=LLMRouter)
    r.complete = AsyncMock(return_value=_llm_response())
    return r


@pytest.fixture
def mock_qdrant() -> MagicMock:
    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    a = MagicMock(spec=QdrantAdapter)
    a.scroll_by_source = AsyncMock(
        return_value=[
            {"chunk_id": "c1", "text": "I know Python well."},
        ]
    )
    return a


@pytest.fixture
def mock_neo4j() -> MagicMock:
    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    a = MagicMock(spec=Neo4jAdapter)
    a.run_query = AsyncMock(return_value=[])
    return a


@pytest.mark.asyncio
async def test_extract_and_write_calls_llm_per_chunk(mock_llm, mock_qdrant, mock_neo4j) -> None:
    from src.services.graph_service import GraphService  # noqa: PLC0415

    mock_qdrant.scroll_by_source = AsyncMock(
        return_value=[
            {"chunk_id": "c1", "text": "chunk one"},
            {"chunk_id": "c2", "text": "chunk two"},
        ]
    )
    service = GraphService(
        llm_router=mock_llm, neo4j_adapter=mock_neo4j, qdrant_adapter=mock_qdrant
    )
    stats = await service.extract_and_write("src-1", "t-1")

    assert mock_llm.complete.call_count == 2
    assert stats["failed_chunks"] == 0


@pytest.mark.asyncio
async def test_extract_and_write_skips_failed_chunks(mock_llm, mock_qdrant, mock_neo4j) -> None:
    from src.services.graph_service import GraphService  # noqa: PLC0415

    mock_qdrant.scroll_by_source = AsyncMock(
        return_value=[
            {"chunk_id": "c1", "text": "chunk one"},
            {"chunk_id": "c2", "text": "chunk two"},
        ]
    )
    # First chunk fails, second succeeds with empty result
    mock_llm.complete = AsyncMock(
        side_effect=[
            RuntimeError("LLM down"),
            _llm_response(entities=[], memories=[], relationships=[]),
        ]
    )
    service = GraphService(
        llm_router=mock_llm, neo4j_adapter=mock_neo4j, qdrant_adapter=mock_qdrant
    )
    stats = await service.extract_and_write("src-1", "t-1")

    assert stats["failed_chunks"] == 1
    assert stats["total_entities"] == 0


@pytest.mark.asyncio
async def test_extract_and_write_filters_low_confidence_entities(
    mock_llm, mock_qdrant, mock_neo4j
) -> None:
    from src.services.graph_service import GraphService  # noqa: PLC0415

    mock_llm.complete = AsyncMock(
        return_value=_llm_response(
            entities=[
                {"name": "Python", "type": "skill", "confidence": 0.9},  # passes
                {"name": "LowConf", "type": "skill", "confidence": 0.3},  # filtered
            ],
            memories=[],
        )
    )
    service = GraphService(
        llm_router=mock_llm, neo4j_adapter=mock_neo4j, qdrant_adapter=mock_qdrant
    )
    stats = await service.extract_and_write("src-1", "t-1")

    assert stats["total_entities"] == 1
    # Only 1 MERGE Concept query (for Python), not 2
    merge_calls = [
        c for c in mock_neo4j.run_query.call_args_list if "MERGE (c:Concept" in str(c.args[0])
    ]
    assert len(merge_calls) == 1


@pytest.mark.asyncio
async def test_concept_writes_use_merge_not_create(mock_llm, mock_qdrant, mock_neo4j) -> None:
    from src.services.graph_service import GraphService  # noqa: PLC0415

    service = GraphService(
        llm_router=mock_llm, neo4j_adapter=mock_neo4j, qdrant_adapter=mock_qdrant
    )
    await service.extract_and_write("src-1", "t-1")

    concept_queries = [
        str(c.args[0])
        for c in mock_neo4j.run_query.call_args_list
        if "MERGE (c:Concept" in str(c.args[0])
    ]
    assert len(concept_queries) >= 1
    # "ON CREATE SET" is a MERGE clause — assert startsWith not absence of "CREATE" to avoid false negative
    assert all(q.strip().startswith("MERGE") for q in concept_queries), (
        "Concepts must use MERGE, not bare CREATE"
    )


@pytest.mark.asyncio
async def test_all_neo4j_calls_include_tenant_id(mock_llm, mock_qdrant, mock_neo4j) -> None:
    from src.services.graph_service import GraphService  # noqa: PLC0415

    service = GraphService(
        llm_router=mock_llm, neo4j_adapter=mock_neo4j, qdrant_adapter=mock_qdrant
    )
    await service.extract_and_write("src-1", "tenant-abc")

    for call in mock_neo4j.run_query.call_args_list:
        assert call.kwargs.get("tenant_id") == "tenant-abc", (
            f"Missing tenant_id in run_query call: {call}"
        )


@pytest.mark.asyncio
async def test_chunk_content_wrapped_in_xml_tags(mock_llm, mock_qdrant, mock_neo4j) -> None:
    from src.services.graph_service import GraphService  # noqa: PLC0415

    mock_qdrant.scroll_by_source = AsyncMock(
        return_value=[
            {"chunk_id": "c1", "text": "my secret content"},
        ]
    )
    service = GraphService(
        llm_router=mock_llm, neo4j_adapter=mock_neo4j, qdrant_adapter=mock_qdrant
    )
    await service.extract_and_write("src-1", "t-1")

    prompt_sent = mock_llm.complete.call_args.kwargs["messages"][0]["content"]
    assert "<user_document>" in prompt_sent
    assert "my secret content" in prompt_sent
    assert "</user_document>" in prompt_sent
