# src/workers/deletion_tasks.py
import structlog

from src.api.dependencies.db import async_session_factory
from src.services.deletion_service import DeletionService

logger = structlog.get_logger()


async def cascade_delete_account(ctx: dict, *, user_id: str) -> dict:  # type: ignore[type-arg]  # noqa: ARG001
    """ARQ task: cascade-delete all data for user_id across all data stores.

    Order is fixed: Storage -> Qdrant -> Neo4j -> PostgreSQL -> Clerk.
    Each step is individually try/excepted — on error, log and continue.
    Partial deletion is always better than no deletion (GDPR best-effort).

    AC-3: Every step logged with action=gdpr_deletion and step name.
    AC-8: Errors logged, cascade continues — never aborted.
    AC-9: Audit trail via structlog before PostgreSQL delete.
    """
    log = logger.bind(tenant_id=user_id, action="gdpr_deletion", job="cascade_delete_account")
    log.info("gdpr_deletion.started")

    service = DeletionService()

    # Step 1: Supabase Storage — all files under /{user_id}/
    try:
        await service.delete_storage_by_tenant(user_id)
        log.info("gdpr_deletion.step_complete", step="storage")
    except Exception as exc:
        log.error("gdpr_deletion.step_failed", step="storage", error=str(exc))

    # Step 2: Qdrant — all vectors where payload.tenant_id = user_id
    try:
        await service.delete_qdrant_by_tenant(user_id)
        log.info("gdpr_deletion.step_complete", step="qdrant")
    except Exception as exc:
        log.error("gdpr_deletion.step_failed", step="qdrant", error=str(exc))

    # Step 3: Neo4j — all nodes and relationships for this tenant
    try:
        await service.delete_neo4j_by_tenant(user_id)
        log.info("gdpr_deletion.step_complete", step="neo4j")
    except Exception as exc:
        log.error("gdpr_deletion.step_failed", step="neo4j", error=str(exc))

    # Step 4: PostgreSQL — all tables in FK-safe order
    # AC-9: Audit trail (structlog) is written at each step before postgres executes.
    try:
        async with async_session_factory() as db:
            await service.delete_postgres_by_tenant(user_id, db)
        log.info("gdpr_deletion.step_complete", step="postgres")
    except Exception as exc:
        log.error("gdpr_deletion.step_failed", step="postgres", error=str(exc))

    # Step 5: Clerk — delete the Clerk user account (invalidates all sessions)
    try:
        await service.delete_clerk_user(user_id)
        log.info("gdpr_deletion.step_complete", step="clerk")
    except Exception as exc:
        log.error("gdpr_deletion.step_failed", step="clerk", error=str(exc))

    log.info("gdpr_deletion.completed", total_steps=5)
    return {"user_id": user_id, "status": "deleted"}
