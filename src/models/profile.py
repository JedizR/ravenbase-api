# src/models/profile.py
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class SystemProfile(SQLModel, table=True):
    __tablename__ = "system_profiles"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str
    description: str | None = None
    icon: str | None = None
    is_default: bool = Field(default=False)
    color: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
