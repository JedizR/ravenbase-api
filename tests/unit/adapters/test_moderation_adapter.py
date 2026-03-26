"""Unit tests for ModerationAdapter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_moderation_response(
    flagged: bool,
    categories: dict[str, bool] | None = None,
) -> MagicMock:
    """Create a mocked moderation response object."""
    result = MagicMock()
    result.flagged = flagged
    cats = MagicMock()
    all_cats = {
        "sexual": False,
        "sexual_minors": False,
        "hate": False,
        "hate_threatening": False,
        "harassment": False,
        "harassment_threatening": False,
        "self_harm": False,
        "self_harm_intent": False,
        "self_harm_instructions": False,
        "violence": False,
        "violence_graphic": False,
    }
    if categories:
        all_cats.update(categories)
    for k, v in all_cats.items():
        setattr(cats, k, v)
    result.categories = cats
    resp = MagicMock()
    resp.results = [result]
    return resp


@pytest.mark.asyncio
async def test_check_content_clean_does_not_raise() -> None:
    """Clean content does not raise."""
    with patch("src.adapters.moderation_adapter.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.moderations.create = AsyncMock(
            return_value=_make_moderation_response(flagged=False)
        )
        mock_openai.return_value = mock_client

        from src.adapters.moderation_adapter import ModerationAdapter  # noqa: PLC0415

        adapter = ModerationAdapter()
        await adapter.check_content("This is fine text.", "src-1", "tenant-1")


@pytest.mark.asyncio
async def test_check_content_hard_reject_raises_hard_moderation_error() -> None:
    """sexual_minors content raises ModerationError(hard=True)."""
    with patch("src.adapters.moderation_adapter.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.moderations.create = AsyncMock(
            return_value=_make_moderation_response(
                flagged=True,
                categories={"sexual_minors": True},
            )
        )
        mock_openai.return_value = mock_client

        from src.adapters.moderation_adapter import (  # noqa: PLC0415
            ModerationAdapter,
            ModerationError,
        )

        adapter = ModerationAdapter()
        with pytest.raises(ModerationError) as exc_info:
            await adapter.check_content("bad content", "src-1", "tenant-1")

    assert exc_info.value.hard is True


@pytest.mark.asyncio
async def test_check_content_soft_reject_raises_soft_moderation_error() -> None:
    """harassment content raises ModerationError(hard=False)."""
    with patch("src.adapters.moderation_adapter.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.moderations.create = AsyncMock(
            return_value=_make_moderation_response(
                flagged=True,
                categories={"harassment": True},
            )
        )
        mock_openai.return_value = mock_client

        from src.adapters.moderation_adapter import (  # noqa: PLC0415
            ModerationAdapter,
            ModerationError,
        )

        adapter = ModerationAdapter()
        with pytest.raises(ModerationError) as exc_info:
            await adapter.check_content("harassment text", "src-1", "tenant-1")

    assert exc_info.value.hard is False


@pytest.mark.asyncio
async def test_check_content_api_unavailable_fails_open() -> None:
    """Moderation API unavailable: logs warning, does NOT raise (fail-open)."""
    with patch("src.adapters.moderation_adapter.AsyncOpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.moderations.create = AsyncMock(side_effect=Exception("timeout"))
        mock_openai.return_value = mock_client

        from src.adapters.moderation_adapter import ModerationAdapter  # noqa: PLC0415

        adapter = ModerationAdapter()
        # Should not raise — fail-open
        await adapter.check_content("text", "src-1", "tenant-1")
