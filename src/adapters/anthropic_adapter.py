# src/adapters/anthropic_adapter.py
from __future__ import annotations

from collections.abc import AsyncIterator

import structlog

from src.adapters.base import BaseAdapter

logger = structlog.get_logger()


class AnthropicAdapter(BaseAdapter):
    """Claude streaming completions.

    anthropic import is lazy (RULE 6 — heavy SDK, avoid startup cost).
    """

    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        model: str,
    ) -> AsyncIterator[str]:
        """Async generator yielding text tokens from Claude streaming API.

        Caller is responsible for handling timeouts (asyncio.timeout).
        Never catches exceptions — let caller decide on error handling.
        """
        from anthropic import AsyncAnthropic  # noqa: PLC0415

        from src.core.config import settings  # noqa: PLC0415

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        log = logger.bind(model=model)
        log.info("anthropic_adapter.stream_completion.started")

        async with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

        log.info("anthropic_adapter.stream_completion.finished")

    def cleanup(self) -> None:
        pass
