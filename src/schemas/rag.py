from uuid import UUID

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    chunk_id: str
    content: str
    source_id: UUID
    memory_id: UUID | None = None
    final_score: float
    semantic_score: float
    recency_weight: float
    page_number: int | None = None
    source_filename: str | None = None
