"""alter_user_id_to_string

Revision ID: 2b57bb9c7c01
Revises: 234dbe10ebe5
Create Date: 2026-03-28 04:08:11.210607

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2b57bb9c7c01'
down_revision: Union[str, Sequence[str], None] = '234dbe10ebe5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change users.id and all user_id FK columns from UUID to VARCHAR."""
    # Step 1: Drop all FK constraints referencing users.id
    op.execute("ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_user_id_fkey")
    op.execute("ALTER TABLE source_authority_weights DROP CONSTRAINT IF EXISTS source_authority_weights_user_id_fkey")
    op.execute("ALTER TABLE system_profiles DROP CONSTRAINT IF EXISTS system_profiles_user_id_fkey")
    op.execute("ALTER TABLE meta_documents DROP CONSTRAINT IF EXISTS meta_documents_user_id_fkey")
    op.execute("ALTER TABLE credit_transactions DROP CONSTRAINT IF EXISTS credit_transactions_user_id_fkey")
    op.execute("ALTER TABLE conflicts DROP CONSTRAINT IF EXISTS conflicts_user_id_fkey")
    op.execute("ALTER TABLE job_statuses DROP CONSTRAINT IF EXISTS job_statuses_user_id_fkey")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_referred_by_user_id_fkey")

    # Step 2: Alter PK and all FK columns (UUID → VARCHAR)
    op.execute("ALTER TABLE users ALTER COLUMN id TYPE VARCHAR USING id::TEXT")
    op.execute("ALTER TABLE users ALTER COLUMN referred_by_user_id TYPE VARCHAR USING referred_by_user_id::TEXT")
    op.execute("ALTER TABLE sources ALTER COLUMN user_id TYPE VARCHAR USING user_id::TEXT")
    op.execute("ALTER TABLE source_authority_weights ALTER COLUMN user_id TYPE VARCHAR USING user_id::TEXT")
    op.execute("ALTER TABLE system_profiles ALTER COLUMN user_id TYPE VARCHAR USING user_id::TEXT")
    op.execute("ALTER TABLE meta_documents ALTER COLUMN user_id TYPE VARCHAR USING user_id::TEXT")
    op.execute("ALTER TABLE credit_transactions ALTER COLUMN user_id TYPE VARCHAR USING user_id::TEXT")
    op.execute("ALTER TABLE conflicts ALTER COLUMN user_id TYPE VARCHAR USING user_id::TEXT")
    op.execute("ALTER TABLE job_statuses ALTER COLUMN user_id TYPE VARCHAR USING user_id::TEXT")

    # Step 3: Re-add FK constraints
    op.execute("ALTER TABLE users ADD CONSTRAINT users_referred_by_user_id_fkey FOREIGN KEY (referred_by_user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE sources ADD CONSTRAINT sources_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE source_authority_weights ADD CONSTRAINT source_authority_weights_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE system_profiles ADD CONSTRAINT system_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE meta_documents ADD CONSTRAINT meta_documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE credit_transactions ADD CONSTRAINT credit_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE conflicts ADD CONSTRAINT conflicts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE job_statuses ADD CONSTRAINT job_statuses_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")


def downgrade() -> None:
    """Revert VARCHAR back to UUID for user identity columns."""
    op.execute("ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_user_id_fkey")
    op.execute("ALTER TABLE source_authority_weights DROP CONSTRAINT IF EXISTS source_authority_weights_user_id_fkey")
    op.execute("ALTER TABLE system_profiles DROP CONSTRAINT IF EXISTS system_profiles_user_id_fkey")
    op.execute("ALTER TABLE meta_documents DROP CONSTRAINT IF EXISTS meta_documents_user_id_fkey")
    op.execute("ALTER TABLE credit_transactions DROP CONSTRAINT IF EXISTS credit_transactions_user_id_fkey")
    op.execute("ALTER TABLE conflicts DROP CONSTRAINT IF EXISTS conflicts_user_id_fkey")
    op.execute("ALTER TABLE job_statuses DROP CONSTRAINT IF EXISTS job_statuses_user_id_fkey")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_referred_by_user_id_fkey")

    op.execute("ALTER TABLE users ALTER COLUMN id TYPE UUID USING id::UUID")
    op.execute("ALTER TABLE users ALTER COLUMN referred_by_user_id TYPE UUID USING referred_by_user_id::UUID")
    op.execute("ALTER TABLE sources ALTER COLUMN user_id TYPE UUID USING user_id::UUID")
    op.execute("ALTER TABLE source_authority_weights ALTER COLUMN user_id TYPE UUID USING user_id::UUID")
    op.execute("ALTER TABLE system_profiles ALTER COLUMN user_id TYPE UUID USING user_id::UUID")
    op.execute("ALTER TABLE meta_documents ALTER COLUMN user_id TYPE UUID USING user_id::UUID")
    op.execute("ALTER TABLE credit_transactions ALTER COLUMN user_id TYPE UUID USING user_id::UUID")
    op.execute("ALTER TABLE conflicts ALTER COLUMN user_id TYPE UUID USING user_id::UUID")
    op.execute("ALTER TABLE job_statuses ALTER COLUMN user_id TYPE UUID USING user_id::UUID")

    op.execute("ALTER TABLE users ADD CONSTRAINT users_referred_by_user_id_fkey FOREIGN KEY (referred_by_user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE sources ADD CONSTRAINT sources_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE source_authority_weights ADD CONSTRAINT source_authority_weights_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE system_profiles ADD CONSTRAINT system_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE meta_documents ADD CONSTRAINT meta_documents_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE credit_transactions ADD CONSTRAINT credit_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE conflicts ADD CONSTRAINT conflicts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
    op.execute("ALTER TABLE job_statuses ADD CONSTRAINT job_statuses_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")

