# src/models/job_status.py
import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class JobStatus(SQLModel, table=True):
    __tablename__ = "job_statuses"  # type: ignore[assignment]

    id: str = Field(primary_key=True)  # ARQ job ID
    user_id: str = Field(foreign_key="users.id", index=True)
    source_id: uuid.UUID | None = Field(default=None, foreign_key="sources.id")
    job_type: str
    status: str = Field(default="queued")
    progress_pct: int = Field(default=0)
    message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
