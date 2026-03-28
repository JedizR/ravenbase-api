# src/schemas/chat.py
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: uuid.UUID | None = None
    profile_id: uuid.UUID | None = None
    model: str | None = None  # "haiku" | "sonnet" | None → defaults to Haiku


class CitationItem(BaseModel):
    memory_id: str | None = None  # str(chunk.memory_id) — may be None for non-memory chunks
    content_preview: str  # first 200 chars of chunk content
    source_id: str  # str(chunk.source_id) — no source_filename on RetrievedChunk


class ChatSessionSummary(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int


class ChatSessionDetail(BaseModel):
    id: uuid.UUID
    title: str | None
    messages: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    message_count: int
