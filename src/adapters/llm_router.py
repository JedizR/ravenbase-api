import asyncio
from typing import Any

import structlog

from src.adapters.base import BaseAdapter

logger = structlog.get_logger()

# task → (primary_model, fallback_model)
_TASK_ROUTING: dict[str, tuple[str, str]] = {
    "entity_extraction": (
        "gemini/gemini-2.5-flash",
        "anthropic/claude-haiku-4-5-20251001",
    ),
    "conflict_classification": (
        "gemini/gemini-2.5-flash",
        "anthropic/claude-haiku-4-5-20251001",
    ),
    "cypher_generation": (
        "gemini/gemini-2.5-flash",
        "anthropic/claude-haiku-4-5-20251001",
    ),
}

_MAX_PRIMARY_ATTEMPTS = 2  # tries before falling back to fallback model


class LLMRouter(BaseAdapter):
    """Routes LLM calls to the correct provider by task type.

    Background tasks: Gemini 2.5 Flash (primary) → Claude Haiku (fallback).
    litellm import is lazy (RULE 6). Never call provider SDKs directly.
    """

    async def complete(
        self,
        task: str,
        messages: list[dict],
        response_format: dict | None = None,
        max_tokens: int = 1024,
        tenant_id: str = "",
    ) -> str:
        """Route a completion request. Returns raw string content.

        Retries primary up to _MAX_PRIMARY_ATTEMPTS times on 429 with exponential
        backoff, then tries fallback once.

        Raises:
            KeyError: unknown task name.
            Exception: all attempts exhausted.
        """
        # Fail fast on unknown task — before importing heavy library
        primary, fallback = _TASK_ROUTING[task]

        import litellm  # noqa: PLC0415

        log = logger.bind(task=task, tenant_id=tenant_id)

        call_kwargs: dict[str, Any] = {
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if response_format:
            call_kwargs["response_format"] = response_format

        # Phase 1: primary model with exponential backoff on 429
        for attempt in range(1, _MAX_PRIMARY_ATTEMPTS + 1):
            try:
                response: Any = await litellm.acompletion(model=primary, **call_kwargs)
                usage = response.usage
                log.info(
                    "llm_router.completed",
                    model=primary,
                    attempt=attempt,
                    prompt_tokens=getattr(usage, "prompt_tokens", None),
                    completion_tokens=getattr(usage, "completion_tokens", None),
                )
                return response.choices[0].message.content or ""
            except Exception as exc:
                is_429 = "429" in str(exc) or "rate_limit" in str(exc).lower()
                if is_429 and attempt < _MAX_PRIMARY_ATTEMPTS:
                    wait = 2 ** (attempt - 1)  # 1s on first retry
                    log.warning(
                        "llm_router.primary_rate_limited",
                        model=primary,
                        attempt=attempt,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    log.warning(
                        "llm_router.primary_failed",
                        model=primary,
                        attempt=attempt,
                        error=str(exc),
                    )
                    break

        # Phase 2: fallback model (one attempt)
        try:
            response: Any = await litellm.acompletion(model=fallback, **call_kwargs)
            usage = response.usage
            log.info(
                "llm_router.fallback_completed",
                model=fallback,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            log.error("llm_router.fallback_failed", model=fallback, error=str(exc))
            raise

    def cleanup(self) -> None:
        pass
