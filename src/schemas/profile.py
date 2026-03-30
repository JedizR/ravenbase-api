# src/schemas/profile.py
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    is_default: bool = False
    created_at: datetime


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = None
    color: str | None = None
    is_default: bool = False


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    icon: str | None = None
    color: str | None = None
    is_default: bool | None = None


class PaginatedProfileResponse(BaseModel):
    items: list[ProfileResponse]
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False
