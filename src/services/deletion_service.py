# src/services/deletion_service.py
import structlog
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.adapters.storage_adapter import StorageAdapter
from src.core.config import settings
from src.services.base import BaseService

logger = structlog.get_logger()

# Content rows only — NO users row (used for archival in STORY-037).
# FK-safe order: children before parents.
_POSTGRES_CONTENT_STATEMENTS = [
    "DELETE FROM data_retention_logs WHERE user_id = :uid",
    "DELETE FROM job_statuses WHERE user_id = :uid",
    "DELETE FROM credit_transactions WHERE user_id = :uid",
    "DELETE FROM chat_sessions WHERE user_id = :uid",
    "DELETE FROM meta_documents WHERE user_id = :uid",
    "DELETE FROM conflicts WHERE user_id = :uid",
    "DELETE FROM source_authority_weights WHERE user_id = :uid",
    "DELETE FROM sources WHERE user_id = :uid",
    "DELETE FROM system_profiles WHERE user_id = :uid",
]

# Full GDPR deletion — content + users row (used by STORY-024).
_POSTGRES_DELETE_STATEMENTS = [
    *_POSTGRES_CONTENT_STATEMENTS,
    "DELETE FROM users WHERE id = :uid",  # Must be last
]


class DeletionService(BaseService):
    """Orchestrates per-step deletion for GDPR Right to Erasure.

    Each method deletes from one data store. Errors are re-raised so callers
    (cascade_delete_account) can log-and-continue per AC-8.
    """

    async def delete_storage_by_tenant(self, user_id: str) -> None:
        """Delete all Supabase Storage files under /{user_id}/."""
        adapter = StorageAdapter()
        await adapter.delete_folder_by_tenant(tenant_id=user_id)

    async def delete_qdrant_by_tenant(self, user_id: str) -> None:
        """Delete all Qdrant vectors where payload.tenant_id = user_id."""
        adapter = QdrantAdapter()
        await adapter.delete_by_filter(tenant_id=user_id)

    async def delete_neo4j_by_tenant(self, user_id: str) -> None:
        """DETACH DELETE all Neo4j nodes for this tenant."""
        adapter = Neo4jAdapter()
        await adapter.delete_all_by_tenant(tenant_id=user_id)

    async def delete_postgres_by_tenant(self, user_id: str, db: AsyncSession) -> None:
        """DELETE all rows for user_id from every table in FK-safe order.

        All SQL strings are schema constants (not user input).
        user_id is always a bind parameter (:uid) — never string-formatted.
        """
        for stmt in _POSTGRES_DELETE_STATEMENTS:
            # stmt is a module-level constant — not user-controlled.
            # Use execute() (SQLAlchemy core) rather than exec() (SQLModel ORM)
            # because exec() is typed only for ORM statements, not raw TextClause.
            await db.execute(text(stmt), {"uid": user_id})
        await db.commit()

    async def delete_content_by_tenant(self, user_id: str, db: AsyncSession) -> None:
        """DELETE content rows for user_id but KEEP the users row.

        Used for cold-data archival (STORY-037). User can still log in after.
        All SQL strings are schema constants — user_id is always a bind param.
        """
        for stmt in _POSTGRES_CONTENT_STATEMENTS:
            await db.execute(text(stmt), {"uid": user_id})
        await db.commit()

    async def delete_clerk_user(self, user_id: str) -> None:
        """Call Clerk Management API to delete the Clerk user account.

        Uses httpx.AsyncClient with the CLERK_SECRET_KEY from settings.
        Clerk account deletion invalidates all active sessions for the user.
        """
        import httpx  # noqa: PLC0415

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
            )
            response.raise_for_status()
