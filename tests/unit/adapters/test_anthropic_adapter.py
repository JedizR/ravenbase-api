# tests/unit/adapters/test_anthropic_adapter.py
"""Unit tests for AnthropicAdapter streaming.

AsyncAnthropic is mocked so tests run without an API key.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_stream_completion_yields_tokens():
    """stream_completion() yields individual text tokens from the stream."""
    from src.adapters.anthropic_adapter import AnthropicAdapter

    mock_stream_ctx = MagicMock()
    # async context manager
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

    async def _fake_text_stream():
        for tok in ["Hello", " world", "!"]:
            yield tok

    mock_stream_ctx.text_stream = _fake_text_stream()

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        adapter = AnthropicAdapter()
        tokens = []
        async for tok in adapter.stream_completion(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="You are helpful.",
            model="claude-haiku-4-5-20251001",
        ):
            tokens.append(tok)

    assert tokens == ["Hello", " world", "!"]


@pytest.mark.asyncio
async def test_stream_completion_passes_correct_model():
    """stream_completion() passes the model argument to the Anthropic client."""
    from src.adapters.anthropic_adapter import AnthropicAdapter

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

    async def _empty_stream():
        return
        yield  # make it an async generator

    mock_stream_ctx.text_stream = _empty_stream()

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream_ctx

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        adapter = AnthropicAdapter()
        async for _ in adapter.stream_completion(
            messages=[{"role": "user", "content": "test"}],
            system_prompt="sys",
            model="claude-sonnet-4-6",
        ):
            pass

    mock_client.messages.stream.assert_called_once()
    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
