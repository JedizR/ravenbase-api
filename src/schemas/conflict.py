# src/schemas/conflict.py
import json

from pydantic import BaseModel, field_validator


class ConflictClassificationResult(BaseModel):
    """Validated LLM output for conflict classification.

    Constructed from raw JSON string returned by LLMRouter.
    Validator rejects unknown classification values before any DB write (RULE 9).
    """

    classification: str  # CONTRADICTION | UPDATE | COMPLEMENT | DUPLICATE
    confidence: float  # 0.0–1.0
    reasoning: str

    @field_validator("classification")
    @classmethod
    def _valid_classification(cls, v: str) -> str:
        allowed = {"CONTRADICTION", "UPDATE", "COMPLEMENT", "DUPLICATE"}
        if v not in allowed:
            raise ValueError(f"Invalid classification: {v!r}. Must be one of {allowed}")
        return v

    @classmethod
    def from_llm_response(cls, raw: str) -> "ConflictClassificationResult":
        """Parse and validate raw LLM JSON string."""
        data = json.loads(raw)
        return cls.model_validate(data)
