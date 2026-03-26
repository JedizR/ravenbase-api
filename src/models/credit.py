# src/models/credit.py
import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class CreditTransaction(SQLModel, table=True):
    __tablename__ = "credit_transactions"  # type: ignore[assignment]

    id: int = Field(default=None, primary_key=True)  # BIGSERIAL
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    amount: int
    balance_after: int
    operation: str
    reference_id: uuid.UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
