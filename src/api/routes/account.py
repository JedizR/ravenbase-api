# src/api/routes/account.py
import structlog
from fastapi import APIRouter, Header, Request

from src.api.dependencies.auth import require_user
from src.schemas.account import AccountDeleteResponse

router = APIRouter(prefix="/v1/account", tags=["account"])
logger = structlog.get_logger()


@router.delete("", response_model=AccountDeleteResponse, status_code=202)
async def delete_account(
    request: Request,
    authorization: str | None = Header(None),
) -> AccountDeleteResponse:
    """Enqueue full account deletion cascade. Returns 202 immediately.

    tenant_id comes exclusively from the validated JWT (require_user).
    The cascade runs in the background: Storage -> Qdrant -> Neo4j -> PostgreSQL -> Clerk.
    SLA: completes within 60 seconds for typical accounts (FR-11-AC-2).
    """
    # Called directly (not via Depends) so tests can patch
    # `src.api.routes.account.require_user` at the module level.
    # FastAPI captures Depends references at decoration time, making them
    # unpatchable; a direct call resolves the name at runtime.
    user = await require_user(authorization)
    user_id: str = user["user_id"]
    log = logger.bind(tenant_id=user_id, action="gdpr_deletion")
    log.info("gdpr_deletion.request_received")

    deterministic_job_id = f"gdpr:{user_id}"
    job = await request.app.state.arq_pool.enqueue_job(
        "cascade_delete_account",
        user_id=user_id,
        _job_id=deterministic_job_id,
    )
    # ARQ returns None if the job already exists (deduplication by _job_id)
    job_id = job.job_id if job is not None else deterministic_job_id

    log.info("gdpr_deletion.job_enqueued", job_id=job_id)
    return AccountDeleteResponse(job_id=job_id)
