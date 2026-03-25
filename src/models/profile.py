# src/models/profile.py
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SystemProfile(SQLModel, table=True):
    __tablename__ = "system_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    is_default: bool = Field(default=False)
    color: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
