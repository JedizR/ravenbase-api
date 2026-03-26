# src/models/source.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class SourceStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class Source(SQLModel, table=True):
    __tablename__ = "sources"  # type: ignore[assignment]
    __table_args__ = (Index("idx_sources_user_ingested", "user_id", "ingested_at"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: uuid.UUID | None = Field(default=None, foreign_key="system_profiles.id")
    original_filename: str
    file_type: str
    mime_type: str
    storage_path: str
    sha256_hash: str = Field(index=True)
    file_size_bytes: int
    status: str = Field(default=SourceStatus.PENDING, index=True)
    chunk_count: int | None = None
    node_count: int | None = None
    error_message: str | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class SourceAuthorityWeight(SQLModel, table=True):
    __tablename__ = "source_authority_weights"  # type: ignore[assignment]

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    source_type: str = Field(primary_key=True)
    weight: int = Field(default=5)
