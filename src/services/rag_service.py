# src/services/rag_service.py
from __future__ import annotations

import hashlib
import re
import uuid as _uuid_mod
from datetime import UTC, datetime
from typing import TypedDict

from structlog import get_logger

from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.schemas.rag import RetrievedChunk
from src.services.base import BaseService

logger = get_logger()

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "her",
        "was",
        "one",
        "our",
        "out",
        "day",
        "get",
        "has",
        "him",
        "his",
        "how",
        "its",
        "may",
        "new",
        "now",
        "old",
        "see",
        "two",
        "who",
        "did",
        "with",
        "that",
        "this",
        "they",
        "from",
        "have",
        "more",
        "when",
        "will",
        "your",
        "been",
        "does",
        "each",
        "just",
        "know",
        "made",
        "make",
        "most",
        "over",
        "said",
        "some",
        "than",
        "them",
        "then",
        "time",
        "very",
        "well",
        "were",
        "what",
        "about",
        "which",
        "their",
        "there",
        "would",
        "could",
        "should",
        "tell",
        "give",
        "take",
        "come",
        "goes",
        "went",
        "like",
        "look",
        "also",
        "into",
        "onto",
        "upon",
        "even",
        "ever",
        "here",
        "away",
        "back",
        "much",
        "many",
        "such",
        "both",
        "long",
        "good",
        "high",
        "last",
        "next",
        "open",
        "same",
        "help",
        "want",
        "need",
        "find",
        "show",
        "feel",
        "keep",
        "hold",
        "move",
        "live",
        "mean",
        "seem",
        "turn",
        "left",
        "puts",
    }
)


def extract_concepts(prompt: str) -> list[str]:
    """Extract meaningful concept words from a prompt for Neo4j graph traversal.

    Simple word extraction: splits on non-alphanumeric, filters stop words and short words.
    Returns lowercase words for case-insensitive Cypher matching (toLower in query).
    """
    if not prompt.strip():
        return []
    words = re.split(r"[^a-zA-Z0-9]+", prompt.lower())
    seen: set[str] = set()
    concepts: list[str] = []
    for word in words:
        if len(word) > 3 and word not in _STOP_WORDS and word not in seen:
            seen.add(word)
            concepts.append(word)
        if len(concepts) == 10:
            break
    return concepts


def _build_profile_filter(profile_id: str | None):  # type: ignore[return]
    """Build an additional Qdrant filter for profile_id scoping. Returns None if no profile."""
    if not profile_id:
        return None
    from qdrant_client.models import FieldCondition, Filter, MatchValue  # noqa: PLC0415

    return Filter(must=[FieldCondition(key="profile_id", match=MatchValue(value=profile_id))])


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _parse_created_at(value: object) -> datetime:
    """Coerce Neo4j DateTime or ISO string or Python datetime to UTC-aware datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    # Neo4j DateTime object — convert via .to_native()
    try:
        return value.to_native().replace(tzinfo=UTC)  # type: ignore[union-attr]
    except AttributeError:
        return datetime.utcnow()


class _Candidate(TypedDict):
    chunk_id: str
    content: str
    source_id: str
    memory_id: str | None
    semantic_score: float
    created_at: datetime
    profile_id: str | None
    page_number: int | None
    content_hash: str


def merge_and_deduplicate(
    qdrant_points: list,
    neo4j_memories: list[dict],
) -> list[_Candidate]:
    """Merge Qdrant ScoredPoints and Neo4j memory dicts, deduplicating by content hash.

    Qdrant entries take precedence (preserve semantic_score and page_number).
    """
    seen_hashes: dict[str, _Candidate] = {}

    # Qdrant results first (they have semantic_score)
    for point in qdrant_points:
        payload = point.payload or {}
        content = payload.get("content", "")
        h = _content_hash(content)
        if h not in seen_hashes:
            seen_hashes[h] = _Candidate(
                chunk_id=str(point.id),
                content=content,
                source_id=str(payload.get("source_id", "")),
                memory_id=payload.get("memory_id"),
                semantic_score=point.score,
                created_at=_parse_created_at(
                    payload.get("created_at", datetime.utcnow().isoformat())
                ),
                profile_id=payload.get("profile_id"),
                page_number=payload.get("page_number"),
                content_hash=h,
            )

    # Neo4j results (semantic_score = 0.0 for graph-only results)
    for mem in neo4j_memories:
        content = mem.get("content", "")
        h = _content_hash(content)
        if h not in seen_hashes:
            source_id_val = mem.get("source_id")
            seen_hashes[h] = _Candidate(
                chunk_id=str(mem.get("chunk_id") or mem.get("memory_id") or ""),
                content=content,
                source_id=str(source_id_val) if source_id_val else "",
                memory_id=str(mem["memory_id"]) if mem.get("memory_id") else None,
                semantic_score=0.0,
                created_at=_parse_created_at(mem.get("created_at", datetime.utcnow())),
                profile_id=mem.get("profile_id"),
                page_number=None,
                content_hash=h,
            )

    return list(seen_hashes.values())


def rerank(candidates: list[_Candidate]) -> list[RetrievedChunk]:
    """Apply scoring formula and return candidates sorted by final_score descending.

    Formula: final_score = (semantic_score × 0.6) + (recency_weight × 0.3) + (profile_match × 0.1)
    recency_weight: decays over months — 1.0 when brand-new, approaches 0 after a year.
    profile_match: 1.0 if chunk belongs to any profile, 0.5 if untagged.
    """
    if not candidates:
        return []

    now = datetime.utcnow()
    result: list[RetrievedChunk] = []

    for c in candidates:
        age_days = max(0, (now - c["created_at"]).days)
        recency_weight = 1.0 / (1.0 + age_days / 30)
        profile_match = 1.0 if c["profile_id"] else 0.5

        final_score = c["semantic_score"] * 0.6 + recency_weight * 0.3 + profile_match * 0.1

        try:
            source_uuid = _uuid_mod.UUID(str(c["source_id"]))
        except (ValueError, AttributeError):
            source_uuid = _uuid_mod.uuid4()

        memory_id_val = c["memory_id"]
        try:
            memory_uuid = _uuid_mod.UUID(str(memory_id_val)) if memory_id_val else None
        except (ValueError, AttributeError):
            memory_uuid = None

        result.append(
            RetrievedChunk(
                chunk_id=c["chunk_id"],
                content=c["content"],
                source_id=source_uuid,
                memory_id=memory_uuid,
                final_score=final_score,
                semantic_score=c["semantic_score"],
                recency_weight=recency_weight,
                page_number=c["page_number"],
            )
        )

    return sorted(result, key=lambda r: r.final_score, reverse=True)


class RAGService(BaseService):
    """Hybrid retrieval service combining Qdrant semantic search + Neo4j graph traversal.

    Adapters are injected for testability; lazily created in production.
    """

    def __init__(
        self,
        qdrant: QdrantAdapter | None = None,
        neo4j: Neo4jAdapter | None = None,
        openai: OpenAIAdapter | None = None,
    ) -> None:
        self._qdrant = qdrant
        self._neo4j = neo4j
        self._openai = openai

    def _get_qdrant(self) -> QdrantAdapter:
        if self._qdrant is None:
            self._qdrant = QdrantAdapter()
        return self._qdrant

    def _get_neo4j(self) -> Neo4jAdapter:
        if self._neo4j is None:
            self._neo4j = Neo4jAdapter()
        return self._neo4j

    def _get_openai(self) -> OpenAIAdapter:
        if self._openai is None:
            self._openai = OpenAIAdapter()
        return self._openai

    def cleanup(self) -> None:
        if self._qdrant:
            self._qdrant.cleanup()
        if self._neo4j:
            self._neo4j.cleanup()
        if self._openai:
            self._openai.cleanup()

    async def retrieve(
        self,
        prompt: str,
        tenant_id: str,
        profile_id: str | None = None,
        limit: int = 10,
    ) -> list[RetrievedChunk]:
        """Three-phase hybrid retrieval: Qdrant kNN → Neo4j traversal → re-rank."""
        if not prompt.strip():
            return []

        log = logger.bind(tenant_id=tenant_id, profile_id=profile_id)

        # Phase 1: Qdrant semantic search
        prompt_embedding = await self._get_openai().embed(prompt)
        qdrant_filter = _build_profile_filter(profile_id)
        qdrant_points = await self._get_qdrant().search(
            query_vector=prompt_embedding,
            tenant_id=tenant_id,
            limit=30,
            additional_filters=qdrant_filter,
        )
        log.info("rag.qdrant_results", count=len(qdrant_points))

        # Phase 2: Neo4j graph traversal
        concept_names = extract_concepts(prompt)
        neo4j_memories = await self._get_neo4j().find_memories_by_concepts(
            concept_names=concept_names,
            tenant_id=tenant_id,
            profile_id=profile_id,
        )
        log.info("rag.neo4j_results", count=len(neo4j_memories))

        # Phase 3: Merge, deduplicate, re-rank
        combined = merge_and_deduplicate(qdrant_points, neo4j_memories)
        ranked = rerank(combined)
        log.info("rag.ranked_results", returned=min(limit, len(ranked)))
        return ranked[:limit]
