# src/schemas/conflict.py
import json
import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, field_validator, model_validator

from src.schemas.common import PaginatedResponse as PaginatedResponse  # re-export  # noqa: PLC0414


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


# ---------------------------------------------------------------------------
# Conflict API schemas (STORY-013)
# ---------------------------------------------------------------------------


class ResolveAction(StrEnum):
    ACCEPT_NEW = "ACCEPT_NEW"
    KEEP_OLD = "KEEP_OLD"
    CUSTOM = "CUSTOM"


class ConflictResponse(BaseModel):
    id: uuid.UUID
    incumbent_content: str
    challenger_content: str
    ai_classification: str
    ai_proposed_resolution: str | None
    confidence_score: float
    incumbent_source_id: uuid.UUID | None
    challenger_source_id: uuid.UUID | None
    status: str
    created_at: datetime


class ResolveRequest(BaseModel):
    action: ResolveAction
    custom_text: str | None = None

    @model_validator(mode="after")
    def _require_custom_text(self) -> "ResolveRequest":
        if self.action == ResolveAction.CUSTOM and not self.custom_text:
            raise ValueError("custom_text is required when action=CUSTOM")
        return self


class GraphMutations(BaseModel):
    superseded_memory_id: str | None = None
    active_memory_id: str | None = None
    new_tags: list[str] = []


class ResolveResponse(BaseModel):
    conflict_id: uuid.UUID
    status: str
    graph_mutations: GraphMutations


class UndoResponse(BaseModel):
    conflict_id: uuid.UUID
    status: str
    message: str
