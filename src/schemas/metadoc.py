# src/schemas/metadoc.py
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    profile_id: UUID | None = None
    model: str | None = None  # "haiku" | "sonnet" | None (uses user's preferred_model)


class GenerateResponse(BaseModel):
    job_id: str
    estimated_credits: int


class MetaDocSummary(BaseModel):
    id: UUID
    title: str
    original_prompt: str
    credits_consumed: int
    generated_at: datetime


class MetaDocDetail(BaseModel):
    id: UUID
    title: str
    original_prompt: str
    content_markdown: str | None
    contributing_memory_count: int
    credits_consumed: int
    model_used: str
    generated_at: datetime
