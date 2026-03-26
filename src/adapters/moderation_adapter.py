from __future__ import annotations

import structlog
from openai import AsyncOpenAI

from src.adapters.base import BaseAdapter
from src.core.config import settings

logger = structlog.get_logger()

# Categories where flagging marks user.is_active = False (hard block)
_HARD_REJECT_CATEGORIES = frozenset(
    [
        "sexual_minors",
        "hate_threatening",
        "violence_graphic",
        "self_harm_intent",
        "self_harm_instructions",
    ]
)


class ModerationError(Exception):
    """Raised when content moderation flags content.

    Attributes:
        hard: True → hard block (deactivate user); False → soft block (fail source only).
    """

    def __init__(self, message: str, *, hard: bool) -> None:
        super().__init__(message)
        self.hard = hard


class ModerationAdapter(BaseAdapter):
    """Wraps OpenAI Moderation API for content safety checks.

    Fail-open on API unavailability (AC-11).
    """

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def check_content(
        self,
        text: str,
        source_id: str,
        tenant_id: str,
    ) -> None:
        """Check text against OpenAI Moderation API.

        Raises:
            ModerationError(hard=True): Hard-reject category flagged → deactivate user.
            ModerationError(hard=False): Soft-reject category flagged → fail source only.
            Returns normally on clean content OR on API unavailability (fail-open).
        """
        log = logger.bind(source_id=source_id, tenant_id=tenant_id)

        if not text.strip():
            return

        try:
            response = await self._get_client().moderations.create(input=text)
        except Exception as exc:
            log.warning("moderation.api_unavailable", error=str(exc))
            return  # fail-open: continue processing

        result = response.results[0]
        if not result.flagged:
            log.debug("moderation.clean")
            return

        # Determine hard vs soft by inspecting flagged categories
        cats = result.categories
        flagged_hard = any(getattr(cats, attr, False) for attr in _HARD_REJECT_CATEGORIES)
        if flagged_hard:
            log.warning("moderation.hard_reject", source_id=source_id, tenant_id=tenant_id)
            raise ModerationError("Content flagged by safety system", hard=True)

        log.warning("moderation.soft_reject", source_id=source_id, tenant_id=tenant_id)
        raise ModerationError("Content flagged by safety system", hard=False)

    def cleanup(self) -> None:
        self._client = None
