# src/services/conflict_service.py
from __future__ import annotations

import uuid

import structlog

from src.adapters.llm_router import LLMRouter
from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.api.dependencies.db import async_session_factory
from src.models.conflict import Conflict, ConflictStatus
from src.models.source import Source, SourceAuthorityWeight
from src.schemas.conflict import ConflictClassificationResult
from src.services.base import BaseService

logger = structlog.get_logger()

# Minimum cosine similarity to consider a pair as candidate
_SIMILARITY_THRESHOLD = 0.87

# Maximum conflicts created per ingestion batch (AC-9)
_MAX_CONFLICTS_PER_BATCH = 5

# Classifications that result in a Conflict DB record
_CONFLICT_CLASSIFICATIONS = {"CONTRADICTION", "UPDATE"}

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
        user_id: uuid.UUID,
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
        except Exception:
            return 5

    async def _load_authority_weight_by_type(
        self,
        user_id: uuid.UUID,
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
