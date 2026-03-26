from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_response(content: str, prompt_tokens: int = 10, completion_tokens: int = 20) -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


@pytest.mark.asyncio
async def test_complete_routes_entity_extraction_to_gemini_flash() -> None:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    mock_resp = _mock_response('{"entities": []}')
    with patch("litellm.acompletion", new=AsyncMock(return_value=mock_resp)) as mock_call:
        result = await LLMRouter().complete(
            task="entity_extraction",
            messages=[{"role": "user", "content": "test"}],
        )

    assert result == '{"entities": []}'
    assert mock_call.call_args.kwargs["model"] == "gemini/gemini-2.5-flash"


@pytest.mark.asyncio
async def test_complete_passes_response_format() -> None:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    mock_resp = _mock_response("{}")
    with patch("litellm.acompletion", new=AsyncMock(return_value=mock_resp)) as mock_call:
        await LLMRouter().complete(
            task="entity_extraction",
            messages=[{"role": "user", "content": "x"}],
            response_format={"type": "json_object"},
        )

    assert mock_call.call_args.kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_complete_retries_primary_on_429_then_succeeds() -> None:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    mock_resp = _mock_response('{"ok": true}')
    call_count = 0

    async def flaky_completion(model: str, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("429 rate_limit exceeded")
        return mock_resp

    with patch("litellm.acompletion", new=flaky_completion):
        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            result = await LLMRouter().complete(
                task="entity_extraction",
                messages=[{"role": "user", "content": "x"}],
            )

    assert result == '{"ok": true}'
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_complete_falls_back_to_haiku_after_primary_exhausted() -> None:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    fallback_resp = _mock_response('{"fallback": true}')
    models_called: list[str] = []

    async def always_fails_gemini(model: str, **kwargs: object) -> object:
        models_called.append(model)
        if "gemini" in model:
            raise Exception("429 rate_limit")
        return fallback_resp

    with patch("litellm.acompletion", new=always_fails_gemini):
        with patch("asyncio.sleep", new=AsyncMock()):
            result = await LLMRouter().complete(
                task="entity_extraction",
                messages=[{"role": "user", "content": "x"}],
            )

    assert result == '{"fallback": true}'
    assert any("claude-haiku" in m for m in models_called)


@pytest.mark.asyncio
async def test_complete_raises_on_unknown_task() -> None:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    with pytest.raises(KeyError):
        await LLMRouter().complete(task="nonexistent_task", messages=[])


@pytest.mark.asyncio
async def test_complete_raises_when_fallback_also_fails() -> None:
    from src.adapters.llm_router import LLMRouter  # noqa: PLC0415

    async def always_fails(model: str, **kwargs: object) -> object:
        raise RuntimeError("provider down")

    with patch("litellm.acompletion", new=always_fails):
        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(RuntimeError, match="provider down"):
                await LLMRouter().complete(
                    task="entity_extraction",
                    messages=[{"role": "user", "content": "x"}],
                )
