"""credits_balance_default_zero

Revision ID: 3a1c9e4f2d80
Revises: 2b57bb9c7c01
Create Date: 2026-03-28 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3a1c9e4f2d80'
down_revision: Union[str, Sequence[str], None] = '2b57bb9c7c01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change users.credits_balance server default from 200 to 0."""
    op.execute("ALTER TABLE users ALTER COLUMN credits_balance SET DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN credits_balance SET DEFAULT 200")
