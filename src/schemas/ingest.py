from uuid import UUID

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    source_id: UUID
    status: str  # "queued" | "duplicate"
    duplicate: bool = False
