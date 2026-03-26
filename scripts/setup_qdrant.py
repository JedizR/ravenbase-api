"""Idempotent Qdrant collection setup. Safe to run multiple times."""

import asyncio

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, Modifier, SparseVectorParams, VectorParams

from src.core.config import settings

COLLECTION_NAME = "ravenbase_chunks"


async def setup_qdrant() -> None:
    client = AsyncQdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
    )
    try:
        existing = await client.get_collections()
        names = [c.name for c in existing.collections]
        if COLLECTION_NAME in names:
            print(f"Collection '{COLLECTION_NAME}' already exists — skipping.")  # noqa: T201
            return

        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            sparse_vectors_config={
                "bm25": SparseVectorParams(modifier=Modifier.IDF),
            },
            on_disk_payload=True,
        )
        print(f"Collection '{COLLECTION_NAME}' created successfully.")  # noqa: T201
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(setup_qdrant())
