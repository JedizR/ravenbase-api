"""add_data_retention_log

Revision ID: 02ab7e1f0d45
Revises: ab9fb0156d8d
Create Date: 2026-03-29 21:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "02ab7e1f0d45"
down_revision: Union[str, None] = "ab9fb0156d8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_retention_logs",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("days_inactive", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qdrant_vectors_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("neo4j_nodes_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_bytes_freed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_retention_logs_user_id", "data_retention_logs", ["user_id"])
    op.create_index(
        "ix_data_retention_logs_user_event",
        "data_retention_logs",
        ["user_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_data_retention_logs_user_event", table_name="data_retention_logs")
    op.drop_index("ix_data_retention_logs_user_id", table_name="data_retention_logs")
    op.drop_table("data_retention_logs")
