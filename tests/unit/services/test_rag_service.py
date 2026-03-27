import uuid
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
