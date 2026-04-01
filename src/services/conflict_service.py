# src/services/conflict_service.py
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from src.adapters.llm_router import LLMRouter
from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.api.dependencies.db import async_session_factory
from src.core.errors import ErrorCode, raise_403, raise_404, raise_409
from src.models.conflict import Conflict, ConflictStatus
from src.models.source import Source, SourceAuthorityWeight
from src.schemas.common import PaginatedResponse
from src.schemas.conflict import (
    ConflictClassificationResult,
    ConflictResponse,
    GraphMutations,
    ResolveAction,
    ResolveResponse,
    UndoResponse,
)
from src.services.base import BaseService

logger = structlog.get_logger()

# Minimum cosine similarity to consider a pair as candidate
_SIMILARITY_THRESHOLD = 0.87

# LLM classification confidence below this threshold: pair is skipped (no Conflict created).
_CONFIDENCE_GATE: float = 0.70

# Maximum conflicts created per ingestion batch (AC-9)
_MAX_CONFLICTS_PER_BATCH = 5

# Classifications that result in a Conflict DB record
_CONFLICT_CLASSIFICATIONS = {"CONTRADICTION", "UPDATE"}

_CUSTOM_RESOLUTION_PROMPT = (
    "You are resolving a memory conflict. "
    "Given the user instruction and the two conflicting memory statements, "
    "output JSON with keys: "
    "active_memory_id (the memory that should be marked active), "
    "superseded_memory_id (the one that should be superseded, or null), "
    "new_tags (list of tag strings, may be empty).\n\n"
    "<incumbent>{incumbent}</incumbent>\n"
    "<challenger>{challenger}</challenger>\n"
    "<user_instruction>{instruction}</user_instruction>"
)

_CLASSIFY_PROMPT = """\
Classify the relationship between these two statements about the same person.

<statement_a>{incumbent}</statement_a>
<statement_b>{challenger}</statement_b>

Return JSON only:
{{"classification": "CONTRADICTION|UPDATE|COMPLEMENT|DUPLICATE", "confidence": 0.0, "reasoning": "one sentence"}}

CONTRADICTION: directly opposing facts
UPDATE: B supersedes A (skill changed, job changed)
COMPLEMENT: adds information without contradiction
DUPLICATE: same meaning, different wording\
"""


class ConflictService(BaseService):
    """Detects contradictions between newly ingested chunks and existing memories.

    Flow: fetch new source vectors → similarity scan → LLM classify →
          write Conflict records + Neo4j edges → auto-resolve → Redis notify.
    """

    def __init__(
        self,
        qdrant: QdrantAdapter | None = None,
        neo4j: Neo4jAdapter | None = None,
        llm_router: LLMRouter | None = None,
    ) -> None:
        self._qdrant = qdrant
        self._neo4j = neo4j
        self._llm_router = llm_router

    def _get_qdrant(self) -> QdrantAdapter:
        if self._qdrant is None:
            self._qdrant = QdrantAdapter()
        return self._qdrant

    def _get_neo4j(self) -> Neo4jAdapter:
        if self._neo4j is None:
            self._neo4j = Neo4jAdapter()
        return self._neo4j

    def _get_llm_router(self) -> LLMRouter:
        if self._llm_router is None:
            self._llm_router = LLMRouter()
        return self._llm_router

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def scan_and_create_conflicts(
        self,
        source_id: str,
        tenant_id: str,
    ) -> dict:
        """Main orchestration: scan new source and create conflict records.

        Returns stats dict with conflict_count, skipped_count, auto_resolved_count.
        """
        log = logger.bind(source_id=source_id, tenant_id=tenant_id)
        log.info("conflict_service.scan_started")

        # 1. Load Source; confirm it exists
        async with async_session_factory() as session:
            source = await session.get(Source, uuid.UUID(source_id))
            if source is None:
                log.warning("conflict_service.source_not_found")
                return {"conflict_count": 0, "skipped_count": 0, "auto_resolved_count": 0}
            challenger_source_id = source.id
            challenger_user_id = source.user_id
            challenger_file_type = source.file_type

        # 2. Fetch vectors for the new source's chunks from Qdrant
        new_chunks = await self._get_qdrant().scroll_by_source_with_vectors(
            source_id=source_id,
            tenant_id=tenant_id,
        )
        if not new_chunks:
            log.info("conflict_service.no_chunks_found")
            return {"conflict_count": 0, "skipped_count": 0, "auto_resolved_count": 0}

        # 3. Find candidate pairs above similarity threshold
        candidates = await self._find_candidates(new_chunks, source_id, tenant_id)
        log.info("conflict_service.candidates_found", candidate_count=len(candidates))

        # 4. Slice to max 5 BEFORE LLM calls (AC-9)
        candidates = candidates[:_MAX_CONFLICTS_PER_BATCH]

        # 5. Process each candidate pair
        conflict_count = 0
        skipped_count = 0
        auto_resolved_count = 0

        async with async_session_factory() as session:
            for incumbent_payload, challenger_payload in candidates:
                incumbent_text = str(incumbent_payload.get("text", ""))
                challenger_text = str(challenger_payload.get("text", ""))
                incumbent_chunk_id = str(incumbent_payload.get("chunk_id", ""))
                challenger_chunk_id = str(challenger_payload.get("chunk_id", ""))
                incumbent_source_id_str = str(incumbent_payload.get("source_id", ""))

                # Classify with LLM
                try:
                    result = await self._classify_pair(incumbent_text, challenger_text, tenant_id)
                except Exception as exc:
                    log.warning(
                        "conflict_service.classify_failed",
                        error=str(exc),
                        incumbent_chunk=incumbent_chunk_id,
                        challenger_chunk=challenger_chunk_id,
                    )
                    skipped_count += 1
                    continue

                log.info(
                    "conflict_service.classified",
                    classification=result.classification,
                    confidence=result.confidence,
                )

                # Skip low-confidence classifications (AC-spec: threshold 0.70)
                if result.confidence < _CONFIDENCE_GATE:
                    log.info(
                        "conflict_service.low_confidence_skipped",
                        confidence=result.confidence,
                        threshold=_CONFIDENCE_GATE,
                    )
                    skipped_count += 1
                    continue

                if result.classification in _CONFLICT_CLASSIFICATIONS:
                    # Load authority weights for auto-resolution
                    incumbent_weight = await self._load_authority_weight(
                        session, challenger_user_id, incumbent_source_id_str
                    )
                    challenger_weight = await self._load_authority_weight_by_type(
                        challenger_user_id, challenger_file_type
                    )

                    # Create Conflict record in PostgreSQL
                    conflict = Conflict(
                        user_id=challenger_user_id,
                        incumbent_memory_id=incumbent_chunk_id,
                        challenger_memory_id=challenger_chunk_id,
                        incumbent_source_id=(
                            uuid.UUID(incumbent_source_id_str) if incumbent_source_id_str else None
                        ),
                        challenger_source_id=challenger_source_id,
                        incumbent_content=incumbent_text,
                        challenger_content=challenger_text,
                        ai_classification=result.classification,
                        confidence_score=result.confidence,
                        ai_proposed_resolution=result.reasoning,
                        status=ConflictStatus.PENDING,
                    )

                    # Auto-resolve if challenger authority delta >= 3
                    if self._maybe_auto_resolve(conflict, incumbent_weight, challenger_weight):
                        auto_resolved_count += 1
                        log.info(
                            "conflict_service.auto_resolved",
                            delta=challenger_weight - incumbent_weight,
                        )

                    session.add(conflict)
                    conflict_count += 1

                    # Write CONTRADICTS edge in Neo4j (AC-6)
                    try:
                        await self._get_neo4j().write_relationships(
                            from_label="Memory",
                            from_id_key="memory_id",
                            from_id=challenger_chunk_id,
                            to_label="Memory",
                            to_id_key="memory_id",
                            to_id=incumbent_chunk_id,
                            rel_type="CONTRADICTS",
                            tenant_id=tenant_id,
                            rel_properties={"confidence": result.confidence},
                        )
                    except Exception as exc:
                        log.warning(
                            "conflict_service.neo4j_contradicts_failed",
                            error=str(exc),
                        )

                elif result.classification == "COMPLEMENT":
                    # AC-10: write TEMPORAL_LINK edge only, no Conflict record
                    try:
                        await self._get_neo4j().write_relationships(
                            from_label="Memory",
                            from_id_key="memory_id",
                            from_id=challenger_chunk_id,
                            to_label="Memory",
                            to_id_key="memory_id",
                            to_id=incumbent_chunk_id,
                            rel_type="TEMPORAL_LINK",
                            tenant_id=tenant_id,
                        )
                    except Exception as exc:
                        log.warning(
                            "conflict_service.neo4j_temporal_link_failed",
                            error=str(exc),
                        )
                    skipped_count += 1

                else:
                    # DUPLICATE — log and skip
                    log.info(
                        "conflict_service.duplicate_skipped",
                        incumbent_chunk=incumbent_chunk_id,
                        challenger_chunk=challenger_chunk_id,
                    )
                    skipped_count += 1

            # 6. Commit all Conflict records at once
            await session.commit()

        # 7. Publish Redis notification AFTER commit (AC-8)
        if conflict_count > 0:
            await self._publish_conflict_notification(tenant_id, conflict_count)

        log.info(
            "conflict_service.scan_completed",
            conflict_count=conflict_count,
            skipped_count=skipped_count,
            auto_resolved_count=auto_resolved_count,
        )
        return {
            "conflict_count": conflict_count,
            "skipped_count": skipped_count,
            "auto_resolved_count": auto_resolved_count,
        }

    # ------------------------------------------------------------------
    # API-facing methods (STORY-013)
    # ------------------------------------------------------------------

    async def list_conflicts(
        self,
        user_id: str,
        status: str | None,
        page: int,
        page_size: int,
        db: AsyncSession,
    ) -> PaginatedResponse[ConflictResponse]:
        """Return paginated conflicts for the given user, newest first."""
        base = select(Conflict).where(Conflict.user_id == user_id)
        if status is not None:
            base = base.where(Conflict.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await db.exec(count_stmt)  # type: ignore[arg-type]
        total: int = count_result.one()

        offset = (page - 1) * page_size
        rows_stmt = (
            base.order_by(Conflict.created_at.desc())  # type: ignore[arg-type]
            .offset(offset)
            .limit(page_size)
        )
        rows_result = await db.exec(rows_stmt)  # type: ignore[arg-type]
        conflicts = rows_result.all()

        items = [
            ConflictResponse(
                id=c.id,
                incumbent_content=c.incumbent_content,
                challenger_content=c.challenger_content,
                ai_classification=c.ai_classification,
                ai_proposed_resolution=c.ai_proposed_resolution,
                confidence_score=c.confidence_score,
                incumbent_source_id=c.incumbent_source_id,
                challenger_source_id=c.challenger_source_id,
                status=c.status,
                created_at=c.created_at,
            )
            for c in conflicts
        ]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + len(items)) < total,
        )

    async def resolve_conflict(
        self,
        conflict_id: str,
        user_id: str,
        action: ResolveAction,
        custom_text: str | None,
        db: AsyncSession,
    ) -> ResolveResponse:
        """Apply a resolution action to a pending conflict."""
        log = logger.bind(conflict_id=conflict_id, user_id=user_id, action=action)

        conflict = await db.get(Conflict, uuid.UUID(conflict_id))
        if conflict is None:
            raise_404(ErrorCode.CONFLICT_NOT_FOUND, "Conflict not found.")

        if conflict.user_id != user_id:
            raise_403(ErrorCode.CONFLICT_FORBIDDEN, "You do not own this conflict.")

        if conflict.status != ConflictStatus.PENDING:
            raise_409(
                ErrorCode.CONFLICT_ALREADY_RESOLVED,
                "Conflict has already been resolved. Undo first.",
            )

        mutations = GraphMutations()

        if action == ResolveAction.ACCEPT_NEW:
            conflict.status = ConflictStatus.RESOLVED_ACCEPT_NEW
            db.add(conflict)
            await db.commit()  # DB committed FIRST

            # Neo4j write AFTER DB commit — with revert on failure
            try:
                await self._get_neo4j().run_query(
                    "MATCH (c:Memory {memory_id: $challenger_id}) "
                    "MATCH (i:Memory {memory_id: $incumbent_id}) "
                    "WHERE c.tenant_id = $tenant_id AND i.tenant_id = $tenant_id "
                    "MERGE (c)-[r:SUPERSEDES]->(i) "
                    "SET c.is_valid = true, i.is_valid = false",
                    challenger_id=conflict.challenger_memory_id,
                    incumbent_id=conflict.incumbent_memory_id,
                    tenant_id=user_id,
                )
            except Exception as neo4j_exc:
                log.error(
                    "conflict_service.neo4j_write_failed_post_commit",
                    conflict_id=conflict_id,
                    error=str(neo4j_exc),
                )
                # Best-effort DB revert to keep systems consistent
                try:
                    conflict.status = ConflictStatus.PENDING
                    conflict.resolved_at = None
                    db.add(conflict)
                    await db.commit()
                except Exception as revert_exc:
                    log.critical(
                        "conflict_service.db_revert_failed",
                        conflict_id=conflict_id,
                        error=str(revert_exc),
                    )
                raise HTTPException(
                    status_code=503,
                    detail={
                        "code": "NEO4J_WRITE_FAILED",
                        "message": "Resolution failed — please retry",
                    },
                ) from neo4j_exc

            mutations = GraphMutations(
                superseded_memory_id=conflict.incumbent_memory_id,
                active_memory_id=conflict.challenger_memory_id,
            )

        elif action == ResolveAction.KEEP_OLD:
            conflict.status = ConflictStatus.RESOLVED_KEEP_OLD
            db.add(conflict)
            await db.commit()

        else:  # CUSTOM
            mutations = await self._apply_custom_resolution(conflict, custom_text or "", user_id)
            conflict.status = ConflictStatus.RESOLVED_CUSTOM
            db.add(conflict)
            await db.commit()

        log.info("conflict_service.resolved", status=conflict.status)
        return ResolveResponse(
            conflict_id=conflict.id,
            status=conflict.status,
            graph_mutations=mutations,
        )

    async def undo_resolution(
        self,
        conflict_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> UndoResponse:
        """Revert a resolution within the 30-second undo window."""
        log = logger.bind(conflict_id=conflict_id, user_id=user_id)

        conflict = await db.get(Conflict, uuid.UUID(conflict_id))
        if conflict is None:
            raise_404(ErrorCode.CONFLICT_NOT_FOUND, "Conflict not found.")

        if conflict.user_id != user_id:
            raise_403(ErrorCode.CONFLICT_FORBIDDEN, "You do not own this conflict.")

        if conflict.status == ConflictStatus.PENDING:
            raise_409(ErrorCode.CONFLICT_NOT_RESOLVED, "Conflict has not been resolved.")

        if conflict.resolved_at is None or (
            datetime.now(UTC) - conflict.resolved_at.replace(tzinfo=UTC) > timedelta(seconds=30)
        ):
            raise_409(
                ErrorCode.UNDO_WINDOW_EXPIRED,
                "Undo window (30 seconds) has expired.",
            )

        if conflict.status == ConflictStatus.RESOLVED_ACCEPT_NEW:
            try:
                await self._get_neo4j().run_query(
                    "MATCH (c:Memory {memory_id: $challenger_id})"
                    "-[r:SUPERSEDES]->"
                    "(i:Memory {memory_id: $incumbent_id}) "
                    "WHERE c.tenant_id = $tenant_id AND i.tenant_id = $tenant_id "
                    "DELETE r "
                    "REMOVE c.is_valid, i.is_valid",
                    challenger_id=conflict.challenger_memory_id,
                    incumbent_id=conflict.incumbent_memory_id,
                    tenant_id=user_id,
                )
            except Exception as exc:
                log.warning("conflict_service.undo_neo4j_failed", error=str(exc))

        conflict.status = ConflictStatus.PENDING
        conflict.resolved_at = None
        conflict.resolution_note = None
        db.add(conflict)
        await db.commit()
        log.info("conflict_service.undone")
        return UndoResponse(
            conflict_id=conflict.id,
            status="pending",
            message="Resolution undone successfully.",
        )

    async def _apply_custom_resolution(
        self,
        conflict: Conflict,
        custom_text: str,
        user_id: str,
    ) -> GraphMutations:
        """Call LLM to determine graph mutations for a custom resolution."""
        prompt = _CUSTOM_RESOLUTION_PROMPT.format(
            incumbent=conflict.incumbent_content,
            challenger=conflict.challenger_content,
            instruction=custom_text,
        )
        raw = await self._get_llm_router().complete(
            task="custom_resolution",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=256,
            tenant_id=user_id,
        )
        try:
            data = json.loads(raw)
            mutations = GraphMutations.model_validate(data)
        except Exception as exc:
            logger.warning(
                "conflict_service.custom_resolution_parse_failed",
                error=str(exc),
                tenant_id=user_id,
            )
            return GraphMutations()

        if mutations.superseded_memory_id and mutations.active_memory_id:
            try:
                await self._get_neo4j().write_relationships(
                    from_label="Memory",
                    from_id_key="memory_id",
                    from_id=mutations.active_memory_id,
                    to_label="Memory",
                    to_id_key="memory_id",
                    to_id=mutations.superseded_memory_id,
                    rel_type="SUPERSEDES",
                    tenant_id=user_id,
                )
            except Exception as exc:
                logger.warning(
                    "conflict_service.custom_supersedes_failed",
                    error=str(exc),
                    tenant_id=user_id,
                )
        return mutations

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _find_candidates(
        self,
        new_chunks: list[tuple[str, list[float], dict]],
        source_id: str,
        tenant_id: str,
    ) -> list[tuple[dict, dict]]:
        """Search Qdrant for similar chunks from other sources above threshold.

        Returns deduplicated list of (incumbent_payload, challenger_payload) pairs.
        """
        from qdrant_client.models import FieldCondition, Filter, MatchValue  # noqa: PLC0415

        # Exclude the new source itself so we don't self-match
        exclude_self = Filter(
            must_not=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]
        )

        seen_pairs: set[tuple[str, str]] = set()
        candidates: list[tuple[dict, dict]] = []

        for _point_id, vec, challenger_payload in new_chunks:
            results = await self._get_qdrant().search(
                query_vector=vec,
                tenant_id=tenant_id,
                limit=10,
                additional_filters=exclude_self,
                score_threshold=_SIMILARITY_THRESHOLD,
            )
            for hit in results:
                incumbent_payload = hit.payload or {}
                incumbent_chunk_id = str(incumbent_payload.get("chunk_id", ""))
                challenger_chunk_id = str(challenger_payload.get("chunk_id", ""))

                # Deduplicate by (incumbent, challenger) pair
                pair_key = (incumbent_chunk_id, challenger_chunk_id)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                candidates.append((incumbent_payload, challenger_payload))

        return candidates

    async def _classify_pair(
        self,
        incumbent_text: str,
        challenger_text: str,
        tenant_id: str,
    ) -> ConflictClassificationResult:
        """Classify a (incumbent, challenger) text pair via LLMRouter.

        RULE 10: user content is wrapped in XML boundary tags.
        RULE 9: LLM output validated against ConflictClassificationResult before return.
        """
        prompt = _CLASSIFY_PROMPT.format(
            incumbent=incumbent_text,
            challenger=challenger_text,
        )
        raw = await self._get_llm_router().complete(
            task="conflict_classification",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=256,
            tenant_id=tenant_id,
        )
        return ConflictClassificationResult.from_llm_response(raw)

    async def _load_authority_weight(
        self,
        session: object,
        user_id: str,
        source_id_str: str,
    ) -> int:
        """Look up authority weight for the incumbent source via its source record."""
        if not source_id_str:
            return 5
        try:
            incumbent_source = await session.get(Source, uuid.UUID(source_id_str))  # type: ignore[union-attr]
            if incumbent_source is None:
                return 5
            return await self._load_authority_weight_by_type(user_id, incumbent_source.file_type)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "conflict_service.authority_weight_lookup_failed",
                error=str(exc),
                source_id=source_id_str,
            )
            return 5

    async def _load_authority_weight_by_type(
        self,
        user_id: str,
        file_type: str,
    ) -> int:
        """Query SourceAuthorityWeight by (user_id, source_type). Default: 5."""
        async with async_session_factory() as session:
            from sqlmodel import select  # noqa: PLC0415

            stmt = select(SourceAuthorityWeight).where(
                SourceAuthorityWeight.user_id == user_id,
                SourceAuthorityWeight.source_type == file_type,
            )
            result = await session.exec(stmt)
            row = result.first()
            return row.weight if row else 5

    @staticmethod
    def _maybe_auto_resolve(
        conflict: Conflict,
        incumbent_weight: int,
        challenger_weight: int,
    ) -> bool:
        """Auto-resolve if challenger authority is 3+ points above incumbent (AC-7)."""
        delta = challenger_weight - incumbent_weight
        if delta >= 3:
            conflict.status = ConflictStatus.AUTO_RESOLVED
            conflict.resolution_note = f"Auto-resolved: challenger authority +{delta}"
            return True
        return False

    async def _publish_conflict_notification(
        self,
        tenant_id: str,
        conflict_count: int,
    ) -> None:
        """Publish to Redis pub/sub after DB commit so SSE inbox subscribers are notified."""
        import json as _json  # noqa: PLC0415

        import redis.asyncio as aioredis  # noqa: PLC0415

        from src.core.config import settings  # noqa: PLC0415

        log = logger.bind(tenant_id=tenant_id)
        r = await aioredis.from_url(settings.REDIS_URL)
        try:
            payload = _json.dumps({"conflict_count": conflict_count})
            await r.publish(f"conflict:new:{tenant_id}", payload)
            log.info("conflict_service.redis_notified", conflict_count=conflict_count)
        finally:
            await r.aclose()

    def cleanup(self) -> None:
        if self._qdrant:
            self._qdrant.cleanup()
        if self._neo4j:
            self._neo4j.cleanup()
