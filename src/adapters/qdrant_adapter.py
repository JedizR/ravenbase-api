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
    ) -> list:
        must_conditions: list[Condition] = list(self._tenant_filter(tenant_id).must or [])  # type: ignore[arg-type]
        if additional_filters and additional_filters.must:
            must_conditions.extend(additional_filters.must)  # type: ignore[arg-type]
        combined = Filter(must=must_conditions)
        result = await self._get_client().query_points(
            collection_name=self.COLLECTION_NAME,
            query=query_vector,
            query_filter=combined,
            limit=limit,
        )
        return result.points

    async def upsert(self, points: list[PointStruct]) -> None:
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

    async def verify_connectivity(self) -> bool:
        try:
            await self._get_client().get_collections()
            return True
        except Exception as exc:
            get_logger().warning("qdrant.connectivity_check_failed", error=str(exc))
            return False

    def cleanup(self) -> None:
        self._client = None
