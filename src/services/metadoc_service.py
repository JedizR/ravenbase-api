# src/services/metadoc_service.py
from __future__ import annotations

import uuid

import structlog
from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.credit_costs import META_DOC_COSTS
from src.core.errors import ErrorCode
from src.models.user import User
from src.schemas.metadoc import GenerateResponse
from src.services.base import BaseService

logger = structlog.get_logger()

MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class MetadocService(BaseService):
    """Orchestrates Meta-Document generation request validation and job enqueueing.

    Business logic only — no direct DB writes here (handled by worker).
    """

    @staticmethod
    def resolve_model(model_alias: str | None, user: User) -> tuple[str, int]:
        """Resolve model alias to full model ID and credit cost.

        Order: request alias → user.preferred_model → Haiku default.
        Free-tier users cannot use Sonnet regardless of request.
        Returns (full_model_id, credit_cost).
        """
        if model_alias:
            model = MODEL_ALIASES.get(model_alias, model_alias)
        else:
            model = user.preferred_model or _DEFAULT_MODEL

        # Free-tier enforcement
        if user.tier != "pro" and model == "claude-sonnet-4-6":
            model = _DEFAULT_MODEL

        credit_cost = META_DOC_COSTS.get(model, META_DOC_COSTS[_DEFAULT_MODEL])
        return model, credit_cost

    async def handle_generate(
        self,
        prompt: str,
        profile_id: str | None,
        model_alias: str | None,
        tenant_id: str,
        arq_pool: object,
        db: AsyncSession,
    ) -> GenerateResponse:
        """Credit check + ARQ enqueue. Returns GenerateResponse with job_id.

        402 raised BEFORE enqueue if user lacks credits (AC-9).
        Credits are NOT deducted here — deducted by worker after success.
        """
        log = logger.bind(tenant_id=tenant_id)

        # Fetch user for tier + credits + preferred_model
        user = await db.get(User, tenant_id)
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={"code": ErrorCode.TENANT_NOT_FOUND, "message": "User not found"},
            )

        model, credit_cost = MetadocService.resolve_model(model_alias, user)
        log.info(
            "metadoc_service.credit_check",
            model=model,
            cost=credit_cost,
            balance=user.credits_balance,
        )

        if user.credits_balance < credit_cost:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": ErrorCode.INSUFFICIENT_CREDITS,
                    "message": (
                        f"Insufficient credits. Required: {credit_cost}, "
                        f"balance: {user.credits_balance}"
                    ),
                },
            )

        job_id = str(uuid.uuid4())
        await arq_pool.enqueue_job(  # type: ignore[union-attr]
            "generate_meta_document",
            job_id=job_id,
            prompt=prompt,
            profile_id=profile_id,
            tenant_id=tenant_id,
            model=model,
            _job_id=job_id,
        )
        log.info("metadoc_service.job_enqueued", job_id=job_id)

        return GenerateResponse(job_id=job_id, estimated_credits=credit_cost)
