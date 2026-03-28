"""add_chat_sessions

Revision ID: ab9fb0156d8d
Revises: 3a1c9e4f2d80
Create Date: 2026-03-29 01:21:28.146336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab9fb0156d8d'
down_revision: Union[str, Sequence[str], None] = '3a1c9e4f2d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import sqlalchemy as sa  # noqa: PLC0415

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("messages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["system_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.execute(
        "CREATE INDEX idx_chat_sessions_user_updated ON chat_sessions (user_id, updated_at DESC)"
    )


def downgrade() -> None:
    op.drop_index("idx_chat_sessions_user_updated", table_name="chat_sessions")
    op.drop_index("idx_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
