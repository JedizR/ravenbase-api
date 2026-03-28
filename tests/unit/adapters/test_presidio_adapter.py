# tests/unit/adapters/test_presidio_adapter.py
"""Unit tests for PresidioAdapter.mask_text — async PII masking with Redis entity map.

presidio_analyzer and presidio_anonymizer engines are mocked so tests run
without loading heavy NLP models.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

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


def _make_redis(existing_map: dict | None = None) -> AsyncMock:
    """Build a mock Redis client. existing_map seeds the entity map already in Redis."""
    mock_redis = AsyncMock()
    raw = json.dumps(existing_map).encode() if existing_map else None
    mock_redis.get = AsyncMock(return_value=raw)
    mock_redis.setex = AsyncMock()
    return mock_redis


@pytest.mark.asyncio
@patch("presidio_analyzer.AnalyzerEngine")
@patch("presidio_anonymizer.AnonymizerEngine")
async def test_mask_text_replaces_person_with_entity_alias(mock_anon_cls, mock_analyzer_cls):
    """PERSON entity in text is replaced with deterministic Entity_000 alias."""
    from src.adapters.presidio_adapter import PresidioAdapter  # noqa: PLC0415

    mock_analyzer = mock_analyzer_cls.return_value
    mock_anonymizer = mock_anon_cls.return_value

    text = "John Smith joined the company."
    mock_analyzer.analyze.return_value = [_make_mock_result(0, 10, "PERSON")]
    mock_anonymizer.anonymize.return_value = _make_mock_anonymized("Entity_000 joined the company.")

    adapter = PresidioAdapter()
    redis = _make_redis()
    masked = await adapter.mask_text(text, job_id="job-001", redis=redis)

    assert masked == "Entity_000 joined the company."
    # Entity map must have been saved to Redis with correct TTL
    redis.setex.assert_awaited_once()
    key, ttl, payload = redis.setex.call_args[0]
    assert key == "pii:map:job-001"
    assert ttl == 3600
    saved_map = json.loads(payload)
    assert saved_map["John Smith"] == "Entity_000"


@pytest.mark.asyncio
@patch("presidio_analyzer.AnalyzerEngine")
@patch("presidio_anonymizer.AnonymizerEngine")
async def test_cross_chunk_consistency(mock_anon_cls, mock_analyzer_cls):
    """Same entity text in two sequential calls gets the same alias via Redis."""
    from src.adapters.presidio_adapter import PresidioAdapter  # noqa: PLC0415

    mock_analyzer = mock_analyzer_cls.return_value
    mock_anonymizer = mock_anon_cls.return_value

    adapter = PresidioAdapter()

    # Call 1 — Redis is empty, entity map starts from scratch
    mock_analyzer.analyze.return_value = [_make_mock_result(0, 10, "PERSON")]
    mock_anonymizer.anonymize.return_value = _make_mock_anonymized("Entity_000 first call.")
    redis1 = _make_redis()
    await adapter.mask_text("John Smith first call.", job_id="job-cross", redis=redis1)

    # Capture map saved after call 1
    _, _, payload = redis1.setex.call_args[0]
    saved_map = json.loads(payload)

    # Call 2 — Redis returns the entity map from call 1
    redis2 = _make_redis(existing_map=saved_map)
    mock_analyzer.analyze.return_value = [_make_mock_result(0, 10, "PERSON")]
    mock_anonymizer.anonymize.return_value = _make_mock_anonymized("Entity_000 second call.")
    await adapter.mask_text("John Smith second call.", job_id="job-cross", redis=redis2)

    _, _, payload2 = redis2.setex.call_args[0]
    map2 = json.loads(payload2)
    assert map2["John Smith"] == "Entity_000"  # same alias, NOT Entity_001


@pytest.mark.asyncio
@patch("presidio_analyzer.AnalyzerEngine")
@patch("presidio_anonymizer.AnonymizerEngine")
async def test_mask_text_no_pii_returns_unchanged(mock_anon_cls, mock_analyzer_cls):
    """Text with no detected PII passes through with its original content."""
    from src.adapters.presidio_adapter import PresidioAdapter  # noqa: PLC0415

    mock_analyzer = mock_analyzer_cls.return_value
    mock_anonymizer = mock_anon_cls.return_value

    text = "The system architecture is well-designed."
    mock_analyzer.analyze.return_value = []
    mock_anonymizer.anonymize.return_value = _make_mock_anonymized(text)

    adapter = PresidioAdapter()
    redis = _make_redis()
    masked = await adapter.mask_text(text, job_id="job-nopii", redis=redis)

    assert masked == text


@pytest.mark.asyncio
@patch("presidio_analyzer.AnalyzerEngine")
@patch("presidio_anonymizer.AnonymizerEngine")
async def test_pii_not_in_llm_payload(mock_anon_cls, mock_analyzer_cls):
    """AC-6: Masked output must NOT contain original PII strings."""
    from src.adapters.presidio_adapter import PresidioAdapter  # noqa: PLC0415

    mock_analyzer = mock_analyzer_cls.return_value
    mock_anonymizer = mock_anon_cls.return_value

    text = "My name is John Smith, email john@example.com"
    mock_analyzer.analyze.return_value = [
        _make_mock_result(11, 21, "PERSON"),
        _make_mock_result(29, 45, "EMAIL_ADDRESS"),
    ]
    mock_anonymizer.anonymize.return_value = _make_mock_anonymized(
        "My name is Entity_000, email Entity_001"
    )

    adapter = PresidioAdapter()
    redis = _make_redis()
    masked = await adapter.mask_text(text, job_id="job-ac6", redis=redis)

    assert "John Smith" not in masked
    assert "john@example.com" not in masked
