from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    job_id: str
    source_id: UUID
    status: str  # "queued" | "duplicate"
    duplicate: bool = False


class SourceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    status: str
    chunk_count: int | None = None
    error_message: str | None = None
    ingested_at: datetime
    completed_at: datetime | None = None


class SourceListResponse(BaseModel):
    items: list[SourceItem]
    total: int


class ProgressEvent(BaseModel):
    progress_pct: int
    message: str
    status: str  # "processing" | "completed" | "failed"


class TextIngestRequest(BaseModel):
    content: str
    profile_id: UUID | None = None
    tags: list[str] = []


class ImportPromptResponse(BaseModel):
    prompt_text: str
    detected_concepts: list[str]
