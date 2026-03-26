from __future__ import annotations

import json
import uuid

import structlog

from src.adapters.llm_router import LLMRouter
from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.schemas.graph import ExtractionResult
from src.services.base import BaseService

logger = structlog.get_logger()

_CONFIDENCE_THRESHOLD = 0.6

# RULE 10: user content wrapped in XML boundary tags
ENTITY_EXTRACTION_PROMPT = """\
Extract entities and facts from the following text chunk.

Return ONLY valid JSON in this exact schema:
{{
  "entities": [
    {{"name": "string", "type": "skill|tool|project|person|org|decision", "confidence": 0.0-1.0}}
  ],
  "memories": [
    {{"content": "A single factual statement about the user", "confidence": 0.0-1.0}}
  ],
  "relationships": [
    {{"from_entity": "name", "to_entity": "name", "type": "USES|WORKED_ON|LED|KNOWS|DECIDED"}}
  ]
}}

Rules:
- Only extract facts explicitly stated in the text
- Memories must be first-person statements ("User worked on...", "User prefers...")
- Confidence < 0.6: skip the entity
- Maximum 10 entities, 5 memories, 5 relationships per chunk

Text:
<user_document>{chunk_content}</user_document>
"""


class GraphService(BaseService):
    """Orchestrates per-chunk entity extraction and Neo4j graph writes.

    All adapters are injection-optional — lazy-created in production, mocked in tests.
    """

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
        neo4j_adapter: Neo4jAdapter | None = None,
        qdrant_adapter: QdrantAdapter | None = None,
    ) -> None:
        self._llm_router = llm_router
        self._neo4j = neo4j_adapter
        self._qdrant = qdrant_adapter

    def _get_llm_router(self) -> LLMRouter:
        if self._llm_router is None:
            self._llm_router = LLMRouter()
        return self._llm_router

    def _get_neo4j(self) -> Neo4jAdapter:
        if self._neo4j is None:
            self._neo4j = Neo4jAdapter()
        return self._neo4j

    def _get_qdrant(self) -> QdrantAdapter:
        if self._qdrant is None:
            self._qdrant = QdrantAdapter()
        return self._qdrant

    async def extract_and_write(self, source_id: str, tenant_id: str) -> dict[str, int]:
        """Fetch all chunks from Qdrant, extract entities per chunk, write to Neo4j.

        Failed chunks are logged and skipped — they do NOT abort the task.

        Returns:
            {"total_entities": int, "total_memories": int, "failed_chunks": int}
        """
        log = logger.bind(tenant_id=tenant_id, source_id=source_id)
        log.info("graph_service.extract_and_write.started")

        chunks = await self._get_qdrant().scroll_by_source(source_id, tenant_id)
        log.info("graph_service.chunks_fetched", chunk_count=len(chunks))

        total_entities = 0
        total_memories = 0
        failed_chunks = 0

        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "unknown")
            chunk_log = log.bind(chunk_id=chunk_id)
            try:
                result = await self._extract_chunk(
                    text=str(chunk.get("text", "")),
                    tenant_id=tenant_id,
                )
                await self._write_to_neo4j(result=result, source_id=source_id, tenant_id=tenant_id)
                total_entities += len(result.entities)
                total_memories += len(result.memories)
                chunk_log.info(
                    "graph_service.chunk_processed",
                    entity_count=len(result.entities),
                    memory_count=len(result.memories),
                )
            except Exception as exc:
                failed_chunks += 1
                chunk_log.warning("graph_service.chunk_failed", error=str(exc))

        log.info(
            "graph_service.extract_and_write.completed",
            total_entities=total_entities,
            total_memories=total_memories,
            failed_chunks=failed_chunks,
        )
        return {
            "total_entities": total_entities,
            "total_memories": total_memories,
            "failed_chunks": failed_chunks,
        }

    async def _extract_chunk(self, text: str, tenant_id: str) -> ExtractionResult:
        prompt = ENTITY_EXTRACTION_PROMPT.format(chunk_content=text)
        raw = await self._get_llm_router().complete(
            task="entity_extraction",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=1024,
            tenant_id=tenant_id,
        )
        data = json.loads(raw)
        result = ExtractionResult(**data)
        result.entities = [e for e in result.entities if e.confidence >= _CONFIDENCE_THRESHOLD]
        result.memories = [m for m in result.memories if m.confidence >= _CONFIDENCE_THRESHOLD]
        return result

    async def _write_to_neo4j(
        self,
        result: ExtractionResult,
        source_id: str,
        tenant_id: str,
    ) -> None:
        neo4j = self._get_neo4j()

        # 1. MERGE Concept nodes — dedup key: {name, tenant_id}
        for entity in result.entities:
            concept_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"concept:{tenant_id}:{entity.name.lower()}")
            )
            await neo4j.run_query(
                "MERGE (c:Concept {name: $name, tenant_id: $tenant_id}) "
                "SET c.concept_id = coalesce(c.concept_id, $concept_id), "
                "c.type = $type, "
                "c.updated_at = datetime()",
                name=entity.name,
                tenant_id=tenant_id,
                concept_id=concept_id,
                type=entity.type,
            )

        # 2. CREATE Memory nodes (each extraction is unique)
        memory_ids: list[str] = []
        for memory in result.memories:
            memory_id = str(uuid.uuid4())
            memory_ids.append(memory_id)
            await neo4j.run_query(
                "CREATE (m:Memory {"
                "memory_id: $memory_id, content: $content, "
                "tenant_id: $tenant_id, source_id: $source_id, created_at: datetime()"
                "})",
                memory_id=memory_id,
                content=memory.content,
                tenant_id=tenant_id,
                source_id=source_id,
            )

        # 3. MERGE Memory → EXTRACTED_FROM → Concept
        for memory_id in memory_ids:
            for entity in result.entities:
                await neo4j.run_query(
                    "MATCH (m:Memory {memory_id: $memory_id, tenant_id: $tenant_id}) "
                    "MATCH (c:Concept {name: $entity_name, tenant_id: $tenant_id}) "
                    "MERGE (m)-[:EXTRACTED_FROM]->(c)",
                    memory_id=memory_id,
                    entity_name=entity.name,
                    tenant_id=tenant_id,
                )

        # 4. MERGE Concept → RELATES_TO → Concept
        for rel in result.relationships:
            await neo4j.run_query(
                "MATCH (a:Concept {name: $from_name, tenant_id: $tenant_id}) "
                "MATCH (b:Concept {name: $to_name, tenant_id: $tenant_id}) "
                "MERGE (a)-[r:RELATES_TO]->(b) "
                "SET r.type = $rel_type",
                from_name=rel.from_entity,
                to_name=rel.to_entity,
                tenant_id=tenant_id,
                rel_type=rel.type,
            )

    def cleanup(self) -> None:
        if self._neo4j:
            self._neo4j.cleanup()
        if self._qdrant:
            self._qdrant.cleanup()
