# src/models/meta_document.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, SQLModel


class MetaDocument(SQLModel, table=True):
    __tablename__ = "meta_documents"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    profile_id: uuid.UUID | None = Field(default=None, foreign_key="system_profiles.id")
    title: str
    original_prompt: str
    parsed_intent: dict | None = Field(default=None, sa_column=Column(JSONB))
    content_markdown: str | None = None
    contributing_memory_ids: list[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String))
    )
    model_used: str = Field(default="claude-sonnet")
    credits_consumed: int = Field(default=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
