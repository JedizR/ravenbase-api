# src/api/routes/chat.py
"""Chat endpoints for STORY-026: Conversational Memory Chat.

Architecture:
  - POST /v1/chat/message: direct SSE streaming (NOT ARQ) — chat must feel instant
  - GET  /v1/chat/sessions: paginated session list
  - GET  /v1/chat/sessions/{session_id}: full session detail
  - DELETE /v1/chat/sessions/{session_id}: delete session (tenant-scoped)

Credit check pattern (AC-9):
  1. get_balance() BEFORE streaming → raise 402 if insufficient
  2. deduct() AFTER full response inside stream_turn() (CreditService.deduct raises 402 too,
     but this pre-check avoids starting the SSE stream if balance is already zero)
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.core.errors import ErrorCode
from src.models.user import User
from src.schemas.chat import (
    ChatMessageRequest,
    ChatSessionDetail,
    ChatSessionSummary,
)
from src.schemas.common import PaginatedResponse
from src.services.chat_service import ChatService

router = APIRouter(prefix="/v1/chat", tags=["chat"])
logger = structlog.get_logger()


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> EventSourceResponse:
    """Stream a chat response grounded in the user's memory base.

    First SSE event: {"type": "session", "session_id": "..."}
    Token events:    {"type": "token", "content": "..."}
    Final event:     {"type": "done", "citations": [...], "credits_consumed": N}
    Error event:     {"type": "error", "message": "..."}

    AC-9: 402 raised BEFORE any retrieval or LLM call if credits insufficient.
    AC-11: session auto-created if session_id not provided.
    """
    log = logger.bind(user_id=user["user_id"])

    # Fetch user for tier check + credit balance
    user_obj = await db.get(User, user["user_id"])
    if user_obj is None:
        raise HTTPException(
            status_code=404,
            detail={"code": ErrorCode.TENANT_NOT_FOUND, "message": "User not found"},
        )

    svc = ChatService()
    resolved_model, credits_needed = ChatService.resolve_model(request.model, user_obj)

    # AC-9: Credit check BEFORE streaming starts (use already-fetched user_obj)
    balance = user_obj.credits_balance
    if balance < credits_needed:
        raise HTTPException(
            status_code=402,
            detail={
                "code": ErrorCode.INSUFFICIENT_CREDITS,
                "message": f"Need {credits_needed} credits, have {balance}",
            },
        )

    # AC-11: Get or create session (tenant-scoped)
    session = await svc.get_or_create_session(
        db=db,
        user_id=user["user_id"],
        session_id=request.session_id,
        profile_id=request.profile_id,
        first_message=request.message,
    )

    log.info(
        "chat.message_received",
        session_id=str(session.id),
        model=resolved_model,
        credits_needed=credits_needed,
    )

    # stream_turn() is an async generator — EventSourceResponse iterates it
    return EventSourceResponse(
        svc.stream_turn(
            session=session,
            user_message=request.message,
            resolved_model=resolved_model,
            credits_needed=credits_needed,
            tenant_id=user["user_id"],
            profile_id=request.profile_id,
            db=db,
        )
    )


@router.get("/sessions", response_model=PaginatedResponse[ChatSessionSummary])
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    profile_id: str | None = Query(default=None),
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PaginatedResponse[ChatSessionSummary]:
    """Paginated list of past sessions for current user (AC-4), newest first."""
    svc = ChatService()
    return await svc.get_sessions(db, user["user_id"], page, page_size, profile_id=profile_id)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: uuid.UUID,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> ChatSessionDetail:
    """Full session with all messages (AC-5). Tenant-scoped — 404 for other users."""
    svc = ChatService()
    return await svc.get_session(db, user["user_id"], session_id)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    user: dict = Depends(require_user),  # type: ignore[type-arg]  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    """Delete session (AC-6). Tenant-scoped — user can only delete own sessions."""
    svc = ChatService()
    await svc.delete_session(db, user["user_id"], session_id)
