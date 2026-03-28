import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)  # Clerk str ID — NOT uuid.UUID
    profile_id: uuid.UUID | None = Field(default=None, foreign_key="system_profiles.id")
    title: str | None = None  # auto-set from first 60 chars of first message
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB),
    )
    # messages format: [{"role": "user"|"assistant", "content": str, "created_at": ISO8601}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
