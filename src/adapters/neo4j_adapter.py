# src/adapters/neo4j_adapter.py
from neo4j import AsyncDriver, AsyncGraphDatabase
from structlog import get_logger

from src.adapters.base import BaseAdapter
from src.core.config import settings


class Neo4jAdapter(BaseAdapter):
    """Async Neo4j graph database adapter.

    __init__ is intentionally fast — no network calls.
    Driver is created lazily on first method call.

    CRITICAL (RULE 11): tenant_id MUST always be passed as a query parameter.
    NEVER use f-strings to embed tenant_id into Cypher queries.
    """

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None

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

    async def verify_connectivity(self) -> bool:
        try:
            await self._get_driver().verify_connectivity()
            return True
        except Exception as exc:
            get_logger().warning("neo4j.connectivity_check_failed", error=str(exc))
            return False

    def cleanup(self) -> None:
        self._driver = None
