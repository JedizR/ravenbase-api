"""add_referral_transactions

Revision ID: 05e8c2b1f7d3
Revises: 02ab7e1f0d45
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "05e8c2b1f7d3"
down_revision: Union[str, Sequence[str], None] = ("6a286e6f5768", "02ab7e1f0d45")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "referral_transactions",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("referrer_user_id", sa.String(), nullable=False),
        sa.Column("referee_user_id", sa.String(), nullable=False),
        sa.Column("referrer_credits_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referee_credits_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trigger_event", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["referrer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["referee_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_referral_transactions_referrer_user_id",
        "referral_transactions",
        ["referrer_user_id"],
    )
    op.create_index(
        "ix_referral_transactions_referee_user_id",
        "referral_transactions",
        ["referee_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_referral_transactions_referee_user_id", table_name="referral_transactions")
    op.drop_index("ix_referral_transactions_referrer_user_id", table_name="referral_transactions")
    op.drop_table("referral_transactions")
