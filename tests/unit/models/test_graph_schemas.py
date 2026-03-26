import pytest


def test_extraction_result_defaults_to_empty_lists() -> None:
    from src.schemas.graph import ExtractionResult  # noqa: PLC0415

    result = ExtractionResult()
    assert result.entities == []
    assert result.memories == []
    assert result.relationships == []


def test_extracted_entity_rejects_confidence_above_1() -> None:
    from pydantic import ValidationError  # noqa: PLC0415

    from src.schemas.graph import ExtractedEntity  # noqa: PLC0415

    with pytest.raises(ValidationError):
        ExtractedEntity(name="X", type="skill", confidence=1.5)


def test_extraction_result_parses_full_llm_response() -> None:
    from src.schemas.graph import ExtractionResult  # noqa: PLC0415

    data = {
        "entities": [{"name": "Python", "type": "skill", "confidence": 0.9}],
        "memories": [{"content": "User knows Python", "confidence": 0.8}],
        "relationships": [{"from_entity": "Python", "to_entity": "FastAPI", "type": "USES"}],
    }
    result = ExtractionResult(**data)
    assert len(result.entities) == 1
    assert result.entities[0].name == "Python"
