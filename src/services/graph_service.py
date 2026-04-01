from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import structlog

from src.adapters.llm_router import LLMRouter
from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.core.config import settings
from src.schemas.graph import ExtractionResult, GraphEdge, GraphNode, GraphResponse
from src.services.base import BaseService

logger = structlog.get_logger()

_CONFIDENCE_THRESHOLD = 0.6
_CHUNK_TIMEOUT_SECONDS: int = 30

# Lookup tables for graph node ID and label extraction (STORY-010)
_NODE_ID_KEYS: dict[str, str] = {
    "Concept": "concept_id",
    "Memory": "memory_id",
    "Source": "source_id",
    "Conflict": "conflict_id",
    "MetaDocument": "doc_id",
    "SystemProfile": "profile_id",
    "User": "user_id",
}

_NODE_LABEL_KEYS: dict[str, str] = {
    "Concept": "name",
    "Memory": "content",
    "Source": "original_filename",
    "Conflict": "classification",
    "MetaDocument": "title",
    "SystemProfile": "name",
    "User": "email",
}

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

    async def extract_and_write(
        self,
        source_id: str,
        tenant_id: str,
        redis=None,  # AsyncRedis client; required when ENABLE_PII_MASKING=True
    ) -> dict[str, int]:
        """Fetch all chunks from Qdrant, extract entities per chunk, write to Neo4j.

        When settings.ENABLE_PII_MASKING is True and redis is provided, each chunk's
        text is masked via PresidioAdapter before being sent to the LLM. The PII entity
        map is stored in Redis at pii:map:{source_id} and deleted in the finally block.

        Each chunk is wrapped in asyncio.timeout(_CHUNK_TIMEOUT_SECONDS). Exceeded
        chunks are counted as failed and skipped — they do NOT abort the task.

        Returns:
            {"total_entities": int, "total_memories": int, "failed_chunks": int}
        """
        log = logger.bind(tenant_id=tenant_id, source_id=source_id)
        log.info("graph_service.extract_and_write.started")

        chunks = await self._get_qdrant().scroll_by_source(source_id, tenant_id)
        log.info("graph_service.chunks_fetched", chunk_count=len(chunks))

        presidio = None
        if settings.ENABLE_PII_MASKING and redis is not None:
            from src.adapters.presidio_adapter import PresidioAdapter  # noqa: PLC0415

            presidio = PresidioAdapter()

        total_entities = 0
        total_memories = 0
        failed_chunks = 0

        try:
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id", "unknown")
                chunk_log = log.bind(chunk_id=chunk_id)
                try:
                    text = str(chunk.get("text", ""))
                    if presidio is not None:
                        text = await presidio.mask_text(text, job_id=source_id, redis=redis)
                    profile_id: str | None = chunk.get("profile_id")
                    async with asyncio.timeout(_CHUNK_TIMEOUT_SECONDS):
                        result = await self._extract_chunk(text=text, tenant_id=tenant_id)
                        await self._write_to_neo4j(
                            result=result,
                            source_id=source_id,
                            tenant_id=tenant_id,
                            profile_id=profile_id,
                        )
                    total_entities += len(result.entities)
                    total_memories += len(result.memories)
                    chunk_log.info(
                        "graph_service.chunk_processed",
                        entity_count=len(result.entities),
                        memory_count=len(result.memories),
                    )
                except TimeoutError:
                    failed_chunks += 1
                    chunk_log.warning(
                        "graph_service.chunk_timeout",
                        timeout_seconds=_CHUNK_TIMEOUT_SECONDS,
                    )
                except Exception as exc:
                    failed_chunks += 1
                    chunk_log.warning(
                        "graph_service.chunk_failed",
                        error=str(exc),
                        exc_type=type(exc).__name__,
                    )
        finally:
            if presidio is not None and redis is not None:
                await redis.delete(f"pii:map:{source_id}")

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
        # Hard caps — spec: 10 entities, 5 memories, 5 relationships per chunk
        result.entities = result.entities[:10]
        result.memories = result.memories[:5]
        result.relationships = result.relationships[:5]
        return result

    async def _write_to_neo4j(
        self,
        result: ExtractionResult,
        source_id: str,
        tenant_id: str,
        profile_id: str | None = None,
    ) -> None:
        neo4j = self._get_neo4j()

        # 1. MERGE Concept nodes — dedup key: {name, tenant_id}
        for entity in result.entities:
            concept_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"concept:{tenant_id}:{entity.name.lower()}")
            )
            await neo4j.run_query(
                "MERGE (c:Concept {name: $name, tenant_id: $tenant_id}) "
                "ON CREATE SET c.concept_id = $concept_id, c.type = $type, c.created_at = datetime() "
                "ON MATCH SET c.updated_at = datetime()",
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

        # 2b. HAS_MEMORY edges: SystemProfile → Memory (when profile_id known)
        if profile_id:
            for memory_id in memory_ids:
                await neo4j.run_query(
                    "MATCH (m:Memory {memory_id: $memory_id, tenant_id: $tenant_id}) "
                    "MERGE (p:SystemProfile {profile_id: $profile_id, tenant_id: $tenant_id}) "
                    "MERGE (p)-[:HAS_MEMORY]->(m)",
                    memory_id=memory_id,
                    profile_id=profile_id,
                    tenant_id=tenant_id,
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

    # ------------------------------------------------------------------
    # Graph Explorer read methods (STORY-010)
    # ------------------------------------------------------------------

    async def get_nodes_for_explorer(
        self,
        tenant_id: str,
        profile_id: str | None,
        node_types: list[str] | None,
        limit: int,
    ) -> GraphResponse:
        """Return all graph nodes + edges for the Graph Explorer UI.

        Cypher returns labels/types as scalars so run_query() dicts carry full metadata.
        Empty graph returns GraphResponse(nodes=[], edges=[]) — never 404.
        RULE 2: tenant_id is a query parameter, never interpolated.
        """
        log = logger.bind(tenant_id=tenant_id, profile_id=profile_id)
        log.info("graph_service.get_nodes_for_explorer.started")

        query = (
            "MATCH (n) "
            "WHERE n.tenant_id = $tenant_id "
            # Profile filter: when profile_id set, traverse HAS_MEMORY edge to get
            # Memory nodes for that profile. When NULL, match all Memory nodes.
            # Concept nodes are tenant-scoped but not profile-scoped.
            "OPTIONAL MATCH (m:Memory)-[:EXTRACTED_FROM]->(c:Concept) "
            "WHERE m.tenant_id = $tenant_id "
            "  AND ($profile_id IS NULL OR EXISTS((:SystemProfile {profile_id: $profile_id, tenant_id: $tenant_id})-[:HAS_MEMORY]->(m))) "
            "RETURN "
            "  labels(n)[0] AS n_type, "
            "  properties(n) AS n_props, "
            "  type(r) AS r_type, "
            "  properties(r) AS r_props, "
            "  labels(m)[0] AS m_type, "
            "  properties(m) AS m_props "
            "LIMIT $limit"
        )
        rows = await self._get_neo4j().run_query(
            query,
            tenant_id=tenant_id,
            profile_id=profile_id,
            limit=limit,
        )
        result = GraphService._rows_to_graph_response(rows, node_types)
        log.info(
            "graph_service.get_nodes_for_explorer.completed",
            node_count=len(result.nodes),
            edge_count=len(result.edges),
        )
        return result

    async def get_neighborhood(
        self,
        node_id: str,
        tenant_id: str,
        hops: int,
        limit: int,
    ) -> GraphResponse:
        """Return the N-hop neighborhood subgraph for a given node.

        Uses two queries (nodes then relationships) with DISTINCT to avoid
        cartesian product. RULE 2: tenant_id always a query parameter.
        """
        log = logger.bind(tenant_id=tenant_id, node_id=node_id)
        log.info("graph_service.get_neighborhood.started")

        nodes_query = (
            "MATCH (start) "
            "WHERE start.tenant_id = $tenant_id "
            "  AND (start.concept_id = $node_id OR start.memory_id = $node_id "
            "       OR start.source_id = $node_id OR start.doc_id = $node_id) "
            "MATCH path = (start)-[*1..$hops]-(neighbor) "
            "WHERE ALL(x IN nodes(path) WHERE x.tenant_id = $tenant_id) "
            "UNWIND nodes(path) AS n "
            "RETURN DISTINCT labels(n)[0] AS n_type, properties(n) AS n_props "
            "LIMIT $limit"
        )
        rels_query = (
            "MATCH (start) "
            "WHERE start.tenant_id = $tenant_id "
            "  AND (start.concept_id = $node_id OR start.memory_id = $node_id "
            "       OR start.source_id = $node_id OR start.doc_id = $node_id) "
            "MATCH path = (start)-[*1..$hops]-(neighbor) "
            "WHERE ALL(x IN nodes(path) WHERE x.tenant_id = $tenant_id) "
            "UNWIND relationships(path) AS r "
            "WITH DISTINCT r "
            "RETURN "
            "  type(r) AS r_type, "
            "  properties(r) AS r_props, "
            "  properties(startNode(r)) AS r_source_props, "
            "  labels(startNode(r))[0] AS r_source_type, "
            "  properties(endNode(r)) AS r_target_props, "
            "  labels(endNode(r))[0] AS r_target_type "
            "LIMIT $limit"
        )
        neo4j = self._get_neo4j()
        node_rows = await neo4j.run_query(
            nodes_query, node_id=node_id, tenant_id=tenant_id, hops=hops, limit=limit
        )
        rel_rows = await neo4j.run_query(
            rels_query, node_id=node_id, tenant_id=tenant_id, hops=hops, limit=limit
        )

        nodes: dict[str, GraphNode] = {}
        for row in node_rows:
            node = self._row_to_graph_node(row["n_props"], row.get("n_type"))
            if node:
                nodes[node.id] = node

        edges: list[GraphEdge] = []
        seen_edges: set[tuple[str, str, str]] = set()
        for row in rel_rows:
            r_type = row.get("r_type") or ""
            source_id = self._extract_node_id(
                row.get("r_source_props") or {}, row.get("r_source_type")
            )
            target_id = self._extract_node_id(
                row.get("r_target_props") or {}, row.get("r_target_type")
            )
            key = (source_id, target_id, r_type)
            if key not in seen_edges and source_id and target_id:
                seen_edges.add(key)
                edges.append(
                    GraphEdge(
                        source=source_id,
                        target=target_id,
                        type=r_type,
                        properties=row.get("r_props") or {},
                    )
                )

        result = GraphResponse(nodes=list(nodes.values()), edges=edges)
        log.info(
            "graph_service.get_neighborhood.completed",
            node_count=len(result.nodes),
            edge_count=len(result.edges),
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rows_to_graph_response(
        rows: list[dict],
        node_types: list[str] | None,
    ) -> GraphResponse:
        """Convert flat OPTIONAL MATCH rows into deduplicated nodes + edges."""
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []
        seen_edges: set[tuple[str, str, str]] = set()
        # Track memory count: concept_id → count of EXTRACTED_FROM Memory edges
        memory_counts: dict[str, int] = {}

        for row in rows:
            # --- primary node (n) ---
            n_node = GraphService._row_to_graph_node(row.get("n_props") or {}, row.get("n_type"))
            if n_node:
                if node_types and n_node.type not in node_types:
                    continue
                if n_node.id not in nodes:
                    nodes[n_node.id] = n_node

            # --- neighbor node (m) from OPTIONAL MATCH ---
            m_props = row.get("m_props") or {}
            m_type = row.get("m_type")
            if m_props:
                m_node = GraphService._row_to_graph_node(m_props, m_type)
                if m_node and m_node.id not in nodes:
                    nodes[m_node.id] = m_node

                # --- edge (r) ---
                r_type = row.get("r_type") or ""
                r_props = row.get("r_props") or {}
                if n_node and m_node and r_type:
                    source_id = n_node.id
                    target_id = m_node.id
                    key = (source_id, target_id, r_type)
                    if key not in seen_edges:
                        seen_edges.add(key)
                        edges.append(
                            GraphEdge(
                                source=source_id,
                                target=target_id,
                                type=r_type,
                                properties=r_props,
                            )
                        )
                    # EXTRACTED_FROM direction: (Memory)-[:EXTRACTED_FROM]->(Concept).
                    # With undirected (n)-[r]-(m) match: when n=Concept and m=Memory,
                    # r_type="EXTRACTED_FROM", so n_node is the Concept getting the count.
                    if r_type == "EXTRACTED_FROM" and m_type == "Memory" and n_node:
                        memory_counts[n_node.id] = memory_counts.get(n_node.id, 0) + 1

        # Apply memory_counts back to Concept nodes
        for node_id, count in memory_counts.items():
            if node_id in nodes:
                nodes[node_id].memory_count = count

        return GraphResponse(nodes=list(nodes.values()), edges=edges)

    @staticmethod
    def _row_to_graph_node(props: dict[str, Any], node_type: str | None) -> GraphNode | None:
        """Convert a property dict + label string into a GraphNode. Returns None if no ID."""
        node_id = GraphService._extract_node_id(props, node_type)
        if not node_id:
            return None
        label = GraphService._extract_node_label(props, node_type)
        return GraphNode(
            id=node_id,
            label=label,
            type=node_type or "unknown",
            properties=props,
            memory_count=0,
        )

    @staticmethod
    def _extract_node_id(props: dict[str, Any], node_type: str | None) -> str:
        """Return the canonical ID for a node given its label and property dict."""
        if node_type and node_type in _NODE_ID_KEYS:
            key = _NODE_ID_KEYS[node_type]
            if key in props:
                return str(props[key])
        # Fallback: try all known ID keys in priority order
        for key in (
            "concept_id",
            "memory_id",
            "source_id",
            "conflict_id",
            "doc_id",
            "profile_id",
            "user_id",
        ):
            if key in props:
                return str(props[key])
        return ""

    @staticmethod
    def _extract_node_label(props: dict[str, Any], node_type: str | None) -> str:
        """Return a human-readable label for the node."""
        if node_type and node_type in _NODE_LABEL_KEYS:
            val = str(props.get(_NODE_LABEL_KEYS[node_type], node_type or "unknown"))
            return val[:100]
        return str(props.get("name", node_type or "unknown"))[:100]
