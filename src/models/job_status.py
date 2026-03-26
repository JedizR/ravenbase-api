# src/models/job_status.py
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class JobStatus(SQLModel, table=True):
    __tablename__ = "job_statuses"

    id: str = Field(primary_key=True)  # ARQ job ID
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    source_id: Optional[uuid.UUID] = Field(default=None, foreign_key="sources.id")
    job_type: str
    status: str = Field(default="queued")
    progress_pct: int = Field(default=0)
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
