# src/models/source.py
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class SourceStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class Source(SQLModel, table=True):
    __tablename__ = "sources"
    __table_args__ = (
        Index("idx_sources_user_ingested", "user_id", "ingested_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: Optional[uuid.UUID] = Field(default=None, foreign_key="system_profiles.id")
    original_filename: str
    file_type: str
    mime_type: str
    storage_path: str
    sha256_hash: str = Field(index=True)
    file_size_bytes: int
    status: str = Field(default=SourceStatus.PENDING, index=True)
    chunk_count: Optional[int] = None
    node_count: Optional[int] = None
    error_message: Optional[str] = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None


class SourceAuthorityWeight(SQLModel, table=True):
    __tablename__ = "source_authority_weights"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    source_type: str = Field(primary_key=True)
    weight: int = Field(default=5)
