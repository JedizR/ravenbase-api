# src/models/user.py
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: str = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    display_name: str | None = None
    avatar_url: str | None = None
    tier: str = Field(default="free")
    credits_balance: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    preferred_model: str = Field(
        default="claude-haiku-4-5-20251001",
        description=(
            "Model for user-initiated generation tasks (meta-docs, chat). "
            "Must be one of: claude-haiku-4-5-20251001, claude-sonnet-4-6"
        ),
    )
    notify_welcome: bool = Field(default=True)
    notify_low_credits: bool = Field(default=True)
    notify_ingestion_complete: bool = Field(default=True)
    referral_code: str = Field(
        default="",
        unique=True,
        index=True,
        description=(
            "First 8 hex chars of a UUID, uppercase. Set on user creation. "
            "Used as: ravenbase.app/register?ref=CODE"
        ),
    )
    referred_by_user_id: str | None = Field(
        default=None,
        foreign_key="users.id",
        description="Clerk user_id of referring user. NULL if organic signup.",
    )
    referral_reward_claimed: bool = Field(
        default=False,
        description=(
            "True after referrer has been credited for this user's first upload. "
            "Prevents double-crediting."
        ),
    )
    low_credits_email_sent_at: datetime | None = Field(
        default=None,
        description=(
            "Timestamp of last low-credits warning email. "
            "Prevents sending the same warning multiple times per billing period. "
            "Reset to None when monthly credits refresh."
        ),
    )
    last_active_at: datetime | None = Field(
        default=None,
        index=True,
        description=(
            "Timestamp of last authenticated API request. Updated at most once "
            "per day per user (debounced in FastAPI middleware) to minimize DB writes."
        ),
    )
    is_archived: bool = Field(
        default=False,
        description=(
            "True when a Free-tier user's data has been purged after 180 days "
            "of inactivity. User record and Clerk identity are KEPT — only storage "
            "data (files, vectors, graph) is deleted. User can still log in and "
            "re-upload. Pro/Team users are NEVER archived."
        ),
    )
    notify_account_deletion: bool = Field(
        default=True,
        description=(
            "Whether to send the 30-day inactivity warning email (day 150 warning). "
            "Part of the notify_* family — user can disable in Settings → Notifications."
        ),
    )
