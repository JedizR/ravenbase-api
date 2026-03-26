# src/models/conflict.py
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class ConflictStatus:
    PENDING = "pending"
    RESOLVED_ACCEPT_NEW = "resolved_accept_new"
    RESOLVED_KEEP_OLD = "resolved_keep_old"
    RESOLVED_CUSTOM = "resolved_custom"
    AUTO_RESOLVED = "auto_resolved"
    DISMISSED = "dismissed"


class Conflict(SQLModel, table=True):
    __tablename__ = "conflicts"
    __table_args__ = (
        Index("idx_conflicts_user_status_created", "user_id", "status", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: Optional[uuid.UUID] = Field(default=None, foreign_key="system_profiles.id")
    incumbent_memory_id: str
    challenger_memory_id: str
    incumbent_source_id: Optional[uuid.UUID] = Field(default=None, foreign_key="sources.id")
    challenger_source_id: Optional[uuid.UUID] = Field(default=None, foreign_key="sources.id")
    incumbent_content: str
    challenger_content: str
    ai_classification: str
    ai_proposed_resolution: Optional[str] = None
    confidence_score: float
    status: str = Field(default=ConflictStatus.PENDING, index=True)
    resolution_note: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
