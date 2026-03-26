from __future__ import annotations

import structlog
from openai import AsyncOpenAI

from src.adapters.base import BaseAdapter
from src.core.config import settings

logger = structlog.get_logger()

_EMBEDDING_MODEL = "text-embedding-3-small"
_BATCH_SIZE = 100


class OpenAIAdapter(BaseAdapter):
    """Wraps OpenAI embeddings API with mandatory batch-100 calls.

    Lazy client init — no network call in __init__.
    NEVER call embed_chunks with a single text in a loop; always pass full list.
    """

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def embed_chunks(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using text-embedding-3-small, batched in groups of 100.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (same length and order as input texts).
        """
        if not texts:
            return []

        log = logger.bind(text_count=len(texts), model=_EMBEDDING_MODEL)
        log.info("openai.embed.started")
        client = self._get_client()
        embeddings: list[list[float]] = []

        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            response = await client.embeddings.create(
                model=_EMBEDDING_MODEL,
                input=batch,
            )
            embeddings.extend([r.embedding for r in response.data])
            log.debug("openai.embed.batch_done", batch_start=i, batch_size=len(batch))

        log.info("openai.embed.completed", vector_count=len(embeddings))
        return embeddings

    def cleanup(self) -> None:
        self._client = None
