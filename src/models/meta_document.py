# src/models/meta_document.py
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, SQLModel


class MetaDocument(SQLModel, table=True):
    __tablename__ = "meta_documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    profile_id: Optional[uuid.UUID] = Field(default=None, foreign_key="system_profiles.id")
    title: str
    original_prompt: str
    parsed_intent: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    content_markdown: Optional[str] = None
    contributing_memory_ids: list[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String))
    )
    model_used: str = Field(default="claude-sonnet")
    credits_consumed: int = Field(default=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
