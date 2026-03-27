# src/adapters/qdrant_adapter.py
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Condition,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
)
from structlog import get_logger

from src.adapters.base import BaseAdapter
from src.core.config import settings


class QdrantAdapter(BaseAdapter):
    """Async Qdrant vector store adapter.

    __init__ is intentionally fast — no network calls.
    Client is created lazily on first method call.
    _tenant_filter() MUST be included in every search/scroll/delete call.
    """

    COLLECTION_NAME: str = "ravenbase_chunks"

    def __init__(self) -> None:
        self._client: AsyncQdrantClient | None = None

    def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
            )
        return self._client

    def _tenant_filter(self, tenant_id: str) -> Filter:
        """ALWAYS include this in every search/scroll/delete call. Security boundary."""
        return Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])

    async def search(
        self,
        query_vector: list[float],
        tenant_id: str,
        limit: int = 10,
        additional_filters: Filter | None = None,
        score_threshold: float | None = None,
    ) -> list:
        must_conditions: list[Condition] = list(self._tenant_filter(tenant_id).must or [])  # type: ignore[arg-type]
        if additional_filters and additional_filters.must:
            must_conditions.extend(additional_filters.must)  # type: ignore[arg-type]
        must_not_conditions: list[Condition] = []
        if additional_filters and additional_filters.must_not:
            must_not_conditions.extend(additional_filters.must_not)  # type: ignore[arg-type]
        combined = Filter(must=must_conditions, must_not=must_not_conditions or None)
        result = await self._get_client().query_points(
            collection_name=self.COLLECTION_NAME,
            query=query_vector,
            query_filter=combined,
            score_threshold=score_threshold,
            limit=limit,
        )
        return result.points

    async def upsert(self, points: list[PointStruct]) -> None:
        for point in points:
            if not (point.payload or {}).get("tenant_id"):
                raise ValueError(
                    f"PointStruct id={point.id!r} is missing required 'tenant_id' in payload"
                )
        await self._get_client().upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
        )

    async def delete_by_filter(
        self,
        tenant_id: str,
        additional_filters: Filter | None = None,
    ) -> None:
        must_conditions: list[Condition] = list(self._tenant_filter(tenant_id).must or [])  # type: ignore[arg-type]
        if additional_filters and additional_filters.must:
            must_conditions.extend(additional_filters.must)  # type: ignore[arg-type]
        f = Filter(must=must_conditions)
        await self._get_client().delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=FilterSelector(filter=f),
        )

    async def count(self, tenant_id: str) -> int:
        result = await self._get_client().count(
            collection_name=self.COLLECTION_NAME,
            count_filter=self._tenant_filter(tenant_id),
            exact=True,
        )
        return result.count

    async def scroll_by_source(
        self,
        source_id: str,
        tenant_id: str,
    ) -> list[dict]:
        """Fetch all chunk payloads for a source. Enforces tenant_id + source_id filter.

        Paginates through all results using Qdrant scroll cursor.
        Returns list of payload dicts (each dict has 'text', 'chunk_id', etc.).
        """
        must_conditions: list[Condition] = list(self._tenant_filter(tenant_id).must or [])  # type: ignore[arg-type]
        must_conditions.append(FieldCondition(key="source_id", match=MatchValue(value=source_id)))
        f = Filter(must=must_conditions)

        payloads: list[dict] = []
        offset: object = None
        while True:
            records, next_offset = await self._get_client().scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=f,
                with_payload=True,
                with_vectors=False,
                limit=100,
                offset=offset,
            )
            payloads.extend(record.payload for record in records if record.payload)
            if next_offset is None:
                break
            offset = next_offset
        return payloads

    async def scroll_by_source_with_vectors(
        self,
        source_id: str,
        tenant_id: str,
    ) -> list[tuple[str, list, dict]]:  # type: ignore[type-arg]
        """Return (point_id, vector, payload) for all chunks of a source.

        Enforces tenant_id + source_id filter. Returns vectors to avoid re-embedding cost.
        Used by conflict detection to search for similar chunks in other sources.
        """
        must_conditions: list[Condition] = list(self._tenant_filter(tenant_id).must or [])  # type: ignore[arg-type]
        must_conditions.append(FieldCondition(key="source_id", match=MatchValue(value=source_id)))
        f = Filter(must=must_conditions)

        results: list[tuple[str, list, dict]] = []  # type: ignore[type-arg]
        offset: object = None
        while True:
            records, next_offset = await self._get_client().scroll(
                collection_name=self.COLLECTION_NAME,
                scroll_filter=f,
                with_payload=True,
                with_vectors=True,
                limit=100,
                offset=offset,
            )
            for record in records:
                if record.payload and record.vector is not None:
                    vec = record.vector
                    # vector may be a named dict (named vectors) or a plain list
                    if isinstance(vec, dict):
                        vec = list(next(iter(vec.values())))
                    results.append((str(record.id), list(vec), dict(record.payload)))  # type: ignore[arg-type]
            if next_offset is None:
                break
            offset = next_offset
        return results

    async def verify_connectivity(self) -> bool:
        try:
            await self._get_client().get_collections()
            return True
        except Exception as exc:
            get_logger().warning("qdrant.connectivity_check_failed", error=str(exc))
            return False

    def cleanup(self) -> None:
        self._client = None
