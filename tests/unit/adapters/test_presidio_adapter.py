# tests/unit/adapters/test_presidio_adapter.py
"""Unit tests for PresidioAdapter PII masking.

presidio_analyzer is mocked so tests run without loading heavy NLP models.
"""
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_result(start: int, end: int, entity_type: str = "PERSON"):
    r = MagicMock()
    r.start = start
    r.end = end
    r.entity_type = entity_type
    return r


def _make_mock_anonymized(text: str):
    a = MagicMock()
    a.text = text
    return a


@patch("presidio_analyzer.AnalyzerEngine")
@patch("presidio_anonymizer.AnonymizerEngine")
def test_mask_for_llm_replaces_person_with_alias(mock_anon_cls, mock_analyzer_cls):
    """PERSON entity in text replaced with deterministic Entity_000 alias."""
    from src.adapters.presidio_adapter import PresidioAdapter

    mock_analyzer = mock_analyzer_cls.return_value
    mock_anonymizer = mock_anon_cls.return_value

    text = "John Smith joined the company."
    mock_result = _make_mock_result(0, 10, "PERSON")
    mock_analyzer.analyze.return_value = [mock_result]
    mock_anonymizer.anonymize.return_value = _make_mock_anonymized(
        "Entity_000 joined the company."
    )

    adapter = PresidioAdapter()
    masked_text, entity_map = adapter.mask_for_llm(text)

    assert masked_text == "Entity_000 joined the company."
    assert "John Smith" in entity_map
    assert entity_map["John Smith"] == "Entity_000"


@patch("presidio_analyzer.AnalyzerEngine")
@patch("presidio_anonymizer.AnonymizerEngine")
def test_mask_for_llm_is_deterministic_across_calls(mock_anon_cls, mock_analyzer_cls):
    """Same entity in two separate mask_for_llm calls gets the same alias."""
    from src.adapters.presidio_adapter import PresidioAdapter

    mock_analyzer = mock_analyzer_cls.return_value
    mock_anonymizer = mock_anon_cls.return_value

    mock_result = _make_mock_result(0, 10, "PERSON")
    mock_analyzer.analyze.return_value = [mock_result]
    mock_anonymizer.anonymize.return_value = _make_mock_anonymized("Entity_000 first call.")

    adapter = PresidioAdapter()
    _, map1 = adapter.mask_for_llm("John Smith first call.")

    mock_anonymizer.anonymize.return_value = _make_mock_anonymized("Entity_000 second call.")
    _, map2 = adapter.mask_for_llm("John Smith second call.")

    assert map1["John Smith"] == map2["John Smith"] == "Entity_000"


@patch("presidio_analyzer.AnalyzerEngine")
@patch("presidio_anonymizer.AnonymizerEngine")
def test_mask_for_llm_no_pii_returns_unchanged(mock_anon_cls, mock_analyzer_cls):
    """Text with no detected PII passes through unchanged."""
    from src.adapters.presidio_adapter import PresidioAdapter

    mock_analyzer = mock_analyzer_cls.return_value
    mock_anonymizer = mock_anon_cls.return_value

    text = "The system architecture is well-designed."
    mock_analyzer.analyze.return_value = []
    mock_anonymizer.anonymize.return_value = _make_mock_anonymized(text)

    adapter = PresidioAdapter()
    masked_text, entity_map = adapter.mask_for_llm(text)

    assert masked_text == text
    assert entity_map == {}
