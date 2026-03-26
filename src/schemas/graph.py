from typing import Any

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    name: str
    type: str  # skill|tool|project|person|org|decision
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedMemory(BaseModel):
    content: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedRelationship(BaseModel):
    from_entity: str
    to_entity: str
    type: str  # USES|WORKED_ON|LED|KNOWS|DECIDED


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = []
    memories: list[ExtractedMemory] = []
    relationships: list[ExtractedRelationship] = []


# --- Graph Explorer API schemas ---


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "Concept" | "Memory" | "Source" | "Conflict" | "MetaDocument"
    properties: dict[str, Any]
    memory_count: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # "RELATES_TO" | "EXTRACTED_FROM" | "CONTRADICTS" | "SUPERSEDES"
    properties: dict[str, Any] = {}


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
