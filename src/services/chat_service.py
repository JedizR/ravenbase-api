# src/services/chat_service.py
from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import structlog
from fastapi import HTTPException
from sqlmodel import desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.credit_costs import CHAT_COSTS
from src.core.errors import ErrorCode
from src.models.chat_session import ChatSession
from src.models.user import User
from src.schemas.chat import (
    ChatSessionDetail,
    ChatSessionSummary,
    CitationItem,
)
from src.schemas.common import PaginatedResponse
from src.schemas.rag import RetrievedChunk
from src.services.base import BaseService
from src.services.credit_service import CreditService

logger = structlog.get_logger()

MODEL_ALIASES: dict[str, str] = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class ChatService(BaseService):
    """Orchestrates multi-turn memory chat: retrieval, streaming, session persistence."""

    @staticmethod
    def resolve_model(model_alias: str | None, user: User) -> tuple[str, int]:
        """Resolve model alias to (full_model_id, credit_cost).

        Order: request alias → user.preferred_model → Haiku default.
        Free-tier users cannot use Sonnet.
        """
        if model_alias:
            model = MODEL_ALIASES.get(model_alias, model_alias)
        else:
            model = user.preferred_model or _DEFAULT_MODEL

        if user.tier != "pro" and model == "claude-sonnet-4-6":
            model = _DEFAULT_MODEL

        credit_cost = CHAT_COSTS.get(model, CHAT_COSTS[_DEFAULT_MODEL])
        return model, credit_cost

    async def get_or_create_session(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: uuid.UUID | None,
        profile_id: uuid.UUID | None,
        first_message: str,
    ) -> ChatSession:
        """Fetch existing session (tenant-scoped) or create new one.

        AC-10: session query is always scoped by user_id — no cross-tenant access.
        AC-11: session auto-created when session_id is None.
        """
        if session_id is not None:
            result = await db.exec(
                select(ChatSession)
                .where(ChatSession.id == session_id)
                .where(ChatSession.user_id == user_id)  # RULE 2 — tenant isolation
            )
            session = result.one_or_none()
            if session is None:
                raise HTTPException(
                    status_code=404,
                    detail={"code": ErrorCode.SESSION_NOT_FOUND, "message": "Session not found"},
                )
            return session

        # Auto-create — title from first 60 chars of first message
        title = first_message[:60].strip() if first_message else None
        session = ChatSession(
            user_id=user_id,
            profile_id=profile_id,
            title=title,
            messages=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    def build_history(self, messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Convert stored messages (last 6) to Anthropic message format.

        Strips 'created_at' and any extra fields — Anthropic only accepts role+content.
        AC-7: at most 6 messages (3 turns) passed as history.
        """
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

    def build_system_prompt(self, chunks: list[RetrievedChunk]) -> str:
        """Build system prompt with retrieved memory context.

        RULE 10: memory content (user-controlled) is wrapped in <memory_context> XML tags.
        Correction: uses str(c.source_id) — RetrievedChunk has no source_filename field.
        """
        context_block = "\n\n".join(
            f"[Memory {i + 1} — source {c.source_id}]:\n{c.content}" for i, c in enumerate(chunks)
        )
        return (
            "You are Ravenbase, an AI assistant with access to the user's personal "
            "knowledge base. Answer questions based ONLY on the provided memories below.\n\n"
            "If the answer is not in the provided memories, say so explicitly. "
            "Be conversational, direct, and concise. When referencing specific memories, "
            'mention the source (e.g., "According to your notes...").\n\n'
            f"<memory_context>\n{context_block}\n</memory_context>"
        )

    def extract_citations(
        self,
        chunks: list[RetrievedChunk],
        filename_map: dict[str, str] | None = None,
    ) -> list[CitationItem]:
        """Build citation list from retrieved chunks.

        filename_map: {str(source_id): original_filename} — from batch DB lookup in stream_turn.
        """
        return [
            CitationItem(
                memory_id=str(c.memory_id) if c.memory_id else None,
                content_preview=c.content[:200],
                source_id=str(c.source_id),
                source_filename=(filename_map or {}).get(str(c.source_id)),
            )
            for c in chunks
        ]

    async def save_turn(
        self,
        db: AsyncSession,
        session: ChatSession,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Append user+assistant messages to session.messages and commit.

        Replaces list (not mutates) so SQLAlchemy detects the JSON column change.
        """
        import bleach  # noqa: PLC0415

        now = datetime.utcnow().isoformat()
        session.messages = session.messages + [
            {"role": "user", "content": user_message, "created_at": now},
            {"role": "assistant", "content": bleach.clean(assistant_response), "created_at": now},
        ]
        session.updated_at = datetime.utcnow()
        db.add(session)
        await db.commit()

    async def stream_turn(
        self,
        session: ChatSession,
        user_message: str,
        resolved_model: str,
        credits_needed: int,
        tenant_id: str,
        profile_id: uuid.UUID | None,
        db: AsyncSession,
    ) -> AsyncGenerator[dict[str, str], None]:
        """Async generator yielding SSE event dicts.

        Sequence:
          1. Yield session event immediately (AC-11)
          2. Retrieve context via RAGService (AC-10: Qdrant filter includes tenant_id)
          3. Build history from last 6 messages (AC-7)
          4. Stream Anthropic response token by token (AC-2: <3s first token)
          5. save_turn() + credit deduct() — only after full response (AC-8)
          6. Yield done event with citations (AC-3)

        Anthropic import is lazy (RULE 6). asyncio.timeout(60) guards against hangs.
        """
        log = logger.bind(tenant_id=tenant_id, session_id=str(session.id))

        # AC-11: session_id in FIRST SSE event
        yield {"data": json.dumps({"type": "session", "session_id": str(session.id)})}

        # Retrieve context — lazy import to comply with RULE 6
        from src.services.rag_service import RAGService  # noqa: PLC0415

        rag = RAGService()
        chunks: list = []
        try:
            async with asyncio.timeout(15):  # 15s timeout for RAG retrieval
                chunks = await rag.retrieve(
                    prompt=user_message,
                    tenant_id=tenant_id,
                    profile_id=str(profile_id) if profile_id else None,
                    limit=8,  # fewer than Meta-Doc — chat is more focused
                )
        except TimeoutError:
            log.warning("chat_service.rag_timeout", message="RAG retrieval timed out, proceeding without context")
        except Exception as exc:
            log.warning("chat_service.rag_error", error=str(exc), message="RAG retrieval failed, proceeding without context")
        finally:
            rag.cleanup()
        log.info("chat_service.retrieved", chunk_count=len(chunks))

        # Batch-fetch source filenames for citations (one query per chat turn)
        source_ids = [str(c.source_id) for c in chunks]
        filename_map: dict[str, str] = {}
        if source_ids:
            from sqlmodel import select as _select  # noqa: PLC0415

            from src.models.source import Source  # noqa: PLC0415

            src_result = await db.exec(
                _select(Source.id, Source.original_filename).where(  # type: ignore[arg-type]
                    Source.id.in_(source_ids)  # type: ignore[attr-defined]
                )
            )
            filename_map = {str(row[0]): row[1] for row in src_result.all()}

        history = self.build_history(session.messages[-6:])  # AC-7: last 6 messages
        system_prompt = self.build_system_prompt(chunks)

        # TODO(STORY-028+): replace AnthropicAdapter with LLMRouter.stream() once streaming is supported
        from src.adapters.anthropic_adapter import AnthropicAdapter  # noqa: PLC0415

        adapter = AnthropicAdapter()
        full_response = ""

        try:
            async with asyncio.timeout(60):
                async for text in adapter.stream_completion(
                    messages=history
                    + [
                        {
                            "role": "user",
                            # RULE 10: user-controlled content wrapped in XML tags
                            "content": f"<user_question>{user_message}</user_question>",
                        }
                    ],
                    system_prompt=system_prompt,
                    model=resolved_model,
                ):
                    full_response += text
                    yield {"data": json.dumps({"type": "token", "content": text})}
        except TimeoutError:
            log.warning("chat_service.stream_timeout")
            yield {"data": json.dumps({"type": "error", "message": "Response timed out"})}
            return
        except Exception as exc:
            log.error("chat_service.stream_error", error=str(exc), exc_info=True)
            err_msg = str(exc)[:200] if str(exc) else "Stream failed"
            yield {"data": json.dumps({"type": "error", "message": err_msg})}
            return

        # Save turn and deduct ONLY after successful full response (AC-8)
        await self.save_turn(db, session, user_message, full_response)

        credit_svc = CreditService()
        await credit_svc.deduct(
            db=db,
            user_id=tenant_id,
            amount=credits_needed,
            operation="chat_message",
            reference_id=session.id,
        )
        log.info("chat_service.turn_complete", credits_deducted=credits_needed)

        citations = self.extract_citations(chunks, filename_map=filename_map)
        yield {
            "data": json.dumps(
                {
                    "type": "done",
                    "citations": [c.model_dump() for c in citations],
                    "credits_consumed": credits_needed,
                }
            )
        }

    async def get_sessions(
        self,
        db: AsyncSession,
        user_id: str,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[ChatSessionSummary]:
        """Paginated list of sessions for user (AC-4), newest first."""
        count_result = await db.exec(
            select(func.count(ChatSession.id)).where(ChatSession.user_id == user_id)  # type: ignore[arg-type]
        )
        total = count_result.one()

        result = await db.exec(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        sessions = list(result.all())

        return PaginatedResponse(
            items=[
                ChatSessionSummary(
                    id=s.id,
                    title=s.title,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    message_count=len(s.messages),
                )
                for s in sessions
            ],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
        )

    async def get_session(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: uuid.UUID,
    ) -> ChatSessionDetail:
        """Full session detail (AC-5), tenant-scoped."""
        result = await db.exec(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)  # RULE 2
        )
        session = result.one_or_none()
        if session is None:
            raise HTTPException(
                status_code=404,
                detail={"code": ErrorCode.SESSION_NOT_FOUND, "message": "Session not found"},
            )
        return ChatSessionDetail(
            id=session.id,
            title=session.title,
            messages=session.messages,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages),
        )

    async def delete_session(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: uuid.UUID,
    ) -> None:
        """Delete session (AC-6), tenant-scoped — user cannot delete others' sessions."""
        result = await db.exec(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)  # RULE 2
        )
        session = result.one_or_none()
        if session is None:
            raise HTTPException(
                status_code=404,
                detail={"code": ErrorCode.SESSION_NOT_FOUND, "message": "Session not found"},
            )
        await db.delete(session)
        await db.commit()
