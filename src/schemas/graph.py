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
