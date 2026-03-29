# src/models/data_retention_log.py
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class DataRetentionLog(SQLModel, table=True):
    __tablename__ = "data_retention_logs"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)  # BIGSERIAL
    user_id: str = Field(index=True, description="Clerk user ID. No FK — intentional audit log design.")
    event_type: str = Field(description="'warning_sent' or 'data_purged'")
    days_inactive: int = Field(default=0)
    sources_deleted: int = Field(default=0)
    qdrant_vectors_deleted: int = Field(default=0)
    neo4j_nodes_deleted: int = Field(default=0)
    storage_bytes_freed: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
