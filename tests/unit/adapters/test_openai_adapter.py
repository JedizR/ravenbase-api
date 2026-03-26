"""Test suite for OpenAI embeddings adapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.openai_adapter import OpenAIAdapter


def _make_embedding_response(n: int) -> MagicMock:
    """Build a mock OpenAI embeddings.create response for n texts."""
    resp = MagicMock()
    resp.data = [MagicMock(embedding=[0.1, 0.2, 0.3]) for _ in range(n)]
    return resp


@pytest.mark.asyncio
async def test_embed_chunks_returns_list_of_vectors() -> None:
    """embed_chunks returns one embedding vector per input text."""
    texts = ["hello world", "second chunk", "third chunk"]

    with patch("src.adapters.openai_adapter.AsyncOpenAI") as mock_open_ai:
        mock_client = MagicMock()
        mock_client.embeddings.create = AsyncMock(
            return_value=_make_embedding_response(len(texts))
        )
        mock_open_ai.return_value = mock_client

        adapter = OpenAIAdapter()
        result = await adapter.embed_chunks(texts)

    assert len(result) == 3
    assert result[0] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_embed_chunks_batches_in_100() -> None:
    """embed_chunks calls embeddings.create once per 100 texts (never per-chunk)."""
    # 250 texts → 3 batches: 100, 100, 50
    texts = [f"chunk {i}" for i in range(250)]
    call_count = 0

    async def _fake_create(model: str, input: list) -> MagicMock:  # noqa: A002
        nonlocal call_count
        call_count += 1
        return _make_embedding_response(len(input))

    with patch("src.adapters.openai_adapter.AsyncOpenAI") as mock_open_ai:
        mock_client = MagicMock()
        mock_client.embeddings.create = _fake_create
        mock_open_ai.return_value = mock_client

        adapter = OpenAIAdapter()
        result = await adapter.embed_chunks(texts)

    assert call_count == 3  # 100 + 100 + 50
    assert len(result) == 250


@pytest.mark.asyncio
async def test_embed_chunks_empty_list_returns_empty() -> None:
    """embed_chunks on empty list returns [] without calling the API."""
    with patch("src.adapters.openai_adapter.AsyncOpenAI") as mock_open_ai:
        mock_client = MagicMock()
        mock_client.embeddings.create = AsyncMock()
        mock_open_ai.return_value = mock_client

        adapter = OpenAIAdapter()
        result = await adapter.embed_chunks([])

    assert result == []
    mock_client.embeddings.create.assert_not_called()
