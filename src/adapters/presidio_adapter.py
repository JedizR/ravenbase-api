# src/adapters/presidio_adapter.py
from __future__ import annotations

import json

import structlog

from src.adapters.base import BaseAdapter

logger = structlog.get_logger()


class PresidioAdapter(BaseAdapter):
    """Deterministic PII masking with cross-chunk consistency via Redis entity map."""

    ENTITY_TYPES = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "CREDIT_CARD",
        "US_SSN",
        "LOCATION",
    ]

    def __init__(self) -> None:
        self._analyzer = None
        self._anonymizer = None

    def _get_analyzer(self):  # type: ignore[return]
        if self._analyzer is None:
            from presidio_analyzer import AnalyzerEngine  # noqa: PLC0415

            self._analyzer = AnalyzerEngine()
        return self._analyzer

    def _get_anonymizer(self):  # type: ignore[return]
        if self._anonymizer is None:
            from presidio_anonymizer import AnonymizerEngine  # noqa: PLC0415

            self._anonymizer = AnonymizerEngine()
        return self._anonymizer

    async def mask_text(self, text: str, job_id: str, redis) -> str:  # type: ignore[type-arg]
        """Mask PII in text using deterministic Entity_NNN aliases.

        Loads existing entity map from Redis (key: pii:map:{job_id}) so the same
        entity text in different chunks receives the same alias across the whole job.
        Saves the updated map back to Redis with TTL 3600 seconds.

        Args:
            text: Input text that may contain PII.
            job_id: ARQ job ID — used as the Redis key namespace.
            redis: Async Redis client (e.g. ctx["redis"] from ARQ worker context).

        Returns:
            Masked text with all PII entities replaced by Entity_NNN aliases.
        """
        from presidio_anonymizer.entities import OperatorConfig  # noqa: PLC0415

        entity_map_key = f"pii:map:{job_id}"
        raw = await redis.get(entity_map_key)
        entity_map: dict[str, str] = json.loads(raw) if raw else {}

        results = self._get_analyzer().analyze(text=text, entities=self.ENTITY_TYPES, language="en")

        for result in results:
            original = text[result.start : result.end]
            if original not in entity_map:
                alias = f"Entity_{len(entity_map):03d}"
                entity_map[original] = alias

        # Build one operator per entity type using a lambda that looks up entity_map
        # by the actual matched text at anonymization time. This correctly handles
        # multiple entities of the same type in one chunk (e.g. two PERSON names
        # get different aliases instead of the second overwriting the first).
        entity_types_found = {r.entity_type for r in results}
        operators = {
            etype: OperatorConfig(
                "custom",
                {"lambda": lambda x, m=entity_map: m.get(x, x)},
            )
            for etype in entity_types_found
        }

        masked_result = self._get_anonymizer().anonymize(
            text=text,
            analyzer_results=results,  # type: ignore[arg-type]
            operators=operators,
        )

        await redis.setex(entity_map_key, 3600, json.dumps(entity_map))
        logger.info("pii.masked", job_id=job_id, entities_found=len(results))
        return masked_result.text

    def cleanup(self) -> None:
        self._analyzer = None
        self._anonymizer = None
