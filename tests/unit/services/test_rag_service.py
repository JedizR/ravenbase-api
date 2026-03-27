import uuid
from unittest.mock import AsyncMock, MagicMock

from src.schemas.rag import RetrievedChunk


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
    from src.adapters.openai_adapter import OpenAIAdapter

    adapter = OpenAIAdapter()
    adapter.embed_chunks = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    result = await adapter.embed("hello world")
    adapter.embed_chunks.assert_called_once_with(["hello world"])
    assert result == [0.1, 0.2, 0.3]
