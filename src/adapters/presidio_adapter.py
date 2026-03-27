# src/adapters/presidio_adapter.py
from __future__ import annotations

import structlog

logger = structlog.get_logger()


class PresidioAdapter:
    """PII masking via Microsoft Presidio.

    All presidio imports are lazy (RULE 6 — heavy NLP models load on first call).
    entity_map is persistent per-instance for consistent pseudonymization across
    multiple chunks sent to the same LLM call.
    """

    def __init__(self) -> None:
        self._analyzer = None
        self._anonymizer = None
        self._entity_map: dict[str, str] = {}

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

    def mask_for_llm(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace PII with deterministic pseudonyms consistent across chunks.

        Returns (masked_text, entity_map_for_this_call).
        The internal _entity_map persists across calls for relational fidelity.
        """
        from presidio_anonymizer.entities import OperatorConfig  # noqa: PLC0415

        results = self._get_analyzer().analyze(text=text, language="en")
        entity_map: dict[str, str] = {}

        for result in results:
            original = text[result.start : result.end]
            if original not in self._entity_map:
                alias = f"Entity_{len(self._entity_map):03d}"
                self._entity_map[original] = alias
            entity_map[original] = self._entity_map[original]

        masked = self._get_anonymizer().anonymize(
            text=text,
            analyzer_results=results,
            operators={
                "PERSON": OperatorConfig(
                    "custom",
                    {"lambda": lambda x: entity_map.get(x, "Person_000")},
                ),
                "EMAIL_ADDRESS": OperatorConfig(
                    "mask", {"chars_to_mask": 8, "masking_char": "*"}
                ),
                "PHONE_NUMBER": OperatorConfig(
                    "replace", {"new_value": "PHONE_REDACTED"}
                ),
                "CREDIT_CARD": OperatorConfig(
                    "replace", {"new_value": "CARD_REDACTED"}
                ),
            },
        )
        return masked.text, entity_map
