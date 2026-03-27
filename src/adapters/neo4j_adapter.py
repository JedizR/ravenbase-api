# src/adapters/neo4j_adapter.py
from neo4j import AsyncDriver, AsyncGraphDatabase
from structlog import get_logger

from src.adapters.base import BaseAdapter
from src.core.config import settings

# Allowlists for Cypher structural identifiers — these are schema constants, not user data.
# Extend as new node labels and relationship types are added in the data model.
_ALLOWED_LABELS: frozenset[str] = frozenset(
    {"User", "SystemProfile", "Source", "Memory", "Concept", "Conflict", "MetaDocument"}
)
_ALLOWED_REL_TYPES: frozenset[str] = frozenset(
    {
        "HAS_PROFILE",
        "HAS_SOURCE",
        "EXTRACTED_FROM",
        "RELATES_TO",
        "CONTRADICTS",
        "SUPERSEDES",
        "CONTAINS",
        "GENERATED",
        "TEMPORAL_LINK",
    }
)


class Neo4jAdapter(BaseAdapter):
    """Async Neo4j graph database adapter.

    __init__ is intentionally fast — no network calls.
    Driver is created lazily on first method call.

    CRITICAL (RULE 11): tenant_id MUST always be passed as a query parameter.
    NEVER use f-strings to embed tenant_id into Cypher queries.
    """

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None

    @staticmethod
    def _validate_label(label: str) -> None:
        if label not in _ALLOWED_LABELS:
            raise ValueError(
                f"Invalid Neo4j node label: {label!r}. Must be one of {_ALLOWED_LABELS}"
            )

    @staticmethod
    def _validate_rel_type(rel_type: str) -> None:
        if rel_type not in _ALLOWED_REL_TYPES:
            raise ValueError(
                f"Invalid Neo4j relationship type: {rel_type!r}. Must be one of {_ALLOWED_REL_TYPES}"
            )

    def _get_driver(self) -> AsyncDriver:
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        return self._driver

    async def run_query(self, query: str, **params: object) -> list[dict]:
        """Execute a Cypher query and return results as a list of dicts.

        Always pass tenant_id as a keyword argument — never interpolate into query string.
        Example:
            await adapter.run_query(
                "MATCH (m:Memory) WHERE m.tenant_id = $tenant_id RETURN m",
                tenant_id=tenant_id,
            )
        """
        async with self._get_driver().session() as session:
            result = await session.run(query, dict(params))  # type: ignore[arg-type]
            return await result.data()

    async def write_nodes(
        self,
        label: str,
        node_id_key: str,
        properties: dict[str, object],
        tenant_id: str,
    ) -> None:
        """MERGE a node by its ID key, set all properties, enforce tenant_id."""
        self._validate_label(label)
        query = (
            f"MERGE (n:{label} {{{node_id_key}: $node_id}}) "
            "SET n += $props "
            "SET n.tenant_id = $tenant_id"
        )
        await self.run_query(
            query,
            node_id=properties[node_id_key],
            props=properties,
            tenant_id=tenant_id,
        )

    async def write_relationships(
        self,
        from_label: str,
        from_id_key: str,
        from_id: str,
        to_label: str,
        to_id_key: str,
        to_id: str,
        rel_type: str,
        tenant_id: str,
        rel_properties: dict[str, object] | None = None,
    ) -> None:
        """MERGE a relationship between two tenant-scoped nodes."""
        self._validate_label(from_label)
        self._validate_label(to_label)
        self._validate_rel_type(rel_type)
        props_clause = "SET r += $rel_props " if rel_properties else ""
        query = (
            f"MATCH (a:{from_label} {{{from_id_key}: $from_id}}) "
            f"MATCH (b:{to_label} {{{to_id_key}: $to_id}}) "
            "WHERE a.tenant_id = $tenant_id AND b.tenant_id = $tenant_id "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"{props_clause}"
        )
        params: dict[str, object] = {
            "from_id": from_id,
            "to_id": to_id,
            "tenant_id": tenant_id,
        }
        if rel_properties:
            params["rel_props"] = rel_properties
        await self.run_query(query, **params)

    async def write_contains_edges(
        self,
        doc_id: str,
        memory_ids: list[str],
        tenant_id: str,
    ) -> None:
        """MERGE a MetaDocument node and CONTAINS edges to each contributing Memory.

        Called after generation completes (AC-8). Each memory_id is a separate
        MERGE to avoid Cypher cartesian-product issues with large lists.
        """
        # 1. MERGE MetaDocument node
        await self.run_query(
            "MERGE (d:MetaDocument {doc_id: $doc_id}) "
            "SET d.tenant_id = $tenant_id",
            doc_id=doc_id,
            tenant_id=tenant_id,
        )
        # 2. MERGE one CONTAINS edge per contributing memory
        for memory_id in memory_ids:
            await self.run_query(
                "MATCH (d:MetaDocument {doc_id: $doc_id}) "
                "MATCH (m:Memory {memory_id: $memory_id}) "
                "WHERE d.tenant_id = $tenant_id AND m.tenant_id = $tenant_id "
                "MERGE (d)-[:CONTAINS]->(m)",
                doc_id=doc_id,
                memory_id=memory_id,
                tenant_id=tenant_id,
            )

    async def find_memories_by_concepts(
        self,
        concept_names: list[str],
        tenant_id: str,
        profile_id: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        """Find Memory nodes related to concept names, scoped by tenant_id.

        RULE 11: tenant_id and all parameters are always passed as Cypher params.
        Returns list of dicts with keys: memory_id, content, created_at, confidence,
        source_id, chunk_id, profile_id.
        """
        if not concept_names:
            return []

        concept_names_lower = [c.lower() for c in concept_names]

        if profile_id:
            query = """
            MATCH (m:Memory)-[:EXTRACTED_FROM]->(c:Concept)
            OPTIONAL MATCH (m)-[:EXTRACTED_FROM]->(s:Source)
            WHERE m.tenant_id = $tenant_id
              AND c.tenant_id = $tenant_id
              AND toLower(c.name) IN $concept_names_lower
              AND m.profile_id = $profile_id
              AND (m.is_valid IS NULL OR m.is_valid = true)
            RETURN m.memory_id AS memory_id, m.content AS content,
                   m.created_at AS created_at, m.confidence AS confidence,
                   s.source_id AS source_id, m.embedding_id AS chunk_id,
                   $profile_id AS profile_id
            ORDER BY m.created_at DESC
            LIMIT $limit
            """
            return await self.run_query(
                query,
                concept_names_lower=concept_names_lower,
                tenant_id=tenant_id,
                profile_id=profile_id,
                limit=limit,
            )
        else:
            query = """
            MATCH (m:Memory)-[:EXTRACTED_FROM]->(c:Concept)
            OPTIONAL MATCH (m)-[:EXTRACTED_FROM]->(s:Source)
            WHERE m.tenant_id = $tenant_id
              AND c.tenant_id = $tenant_id
              AND toLower(c.name) IN $concept_names_lower
              AND (m.is_valid IS NULL OR m.is_valid = true)
            RETURN m.memory_id AS memory_id, m.content AS content,
                   m.created_at AS created_at, m.confidence AS confidence,
                   s.source_id AS source_id, m.embedding_id AS chunk_id,
                   m.profile_id AS profile_id
            ORDER BY m.created_at DESC
            LIMIT $limit
            """
            return await self.run_query(
                query,
                concept_names_lower=concept_names_lower,
                tenant_id=tenant_id,
                limit=limit,
            )

    async def verify_connectivity(self) -> bool:
        try:
            await self._get_driver().verify_connectivity()
            return True
        except Exception as exc:
            get_logger().warning("neo4j.connectivity_check_failed", error=str(exc))
            return False

    def cleanup(self) -> None:
        self._driver = None
