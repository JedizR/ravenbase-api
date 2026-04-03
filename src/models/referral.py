# src/models/referral.py
from datetime import datetime

from sqlmodel import Field, SQLModel


class ReferralTransaction(SQLModel, table=True):
    __tablename__ = "referral_transactions"  # type: ignore[assignment]

    id: int = Field(default=None, primary_key=True)
    referrer_user_id: str = Field(foreign_key="users.id", index=True)
    referee_user_id: str = Field(foreign_key="users.id", index=True)
    referrer_credits_awarded: int = Field(default=0)
    referee_credits_awarded: int = Field(default=0)
    trigger_event: str = Field(
        description="signup | first_upload",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
