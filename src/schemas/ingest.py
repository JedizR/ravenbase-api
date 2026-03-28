from uuid import UUID

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    source_id: UUID
    status: str  # "queued" | "duplicate"
    duplicate: bool = False


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
