# src/services/graph_query_service.py
from __future__ import annotations

import re
import time

import structlog

from src.adapters.llm_router import LLMRouter
from src.adapters.neo4j_adapter import Neo4jAdapter
from src.core.errors import ErrorCode, raise_422
from src.schemas.graph import GraphQueryResponse, GraphResponse
from src.services.base import BaseService
from src.services.graph_service import GraphService

logger = structlog.get_logger()

# AC-3: reject Cypher with write keywords (case-insensitive, word-boundary).
# Also catches CALL db.* and CALL apoc.* which invoke write procedures.
CYPHER_WRITE_KEYWORDS: re.Pattern[str] = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP)\b"
    r"|CALL\s+db\."
    r"|CALL\s+apoc\.",
    re.IGNORECASE,
)

# RULE 10: user query wrapped in <user_query> XML tags.
# RETURN clause is mandated so that GraphService._rows_to_graph_response()
# can parse the results directly (avoids duplicating node/edge parsing logic).
CYPHER_GENERATION_PROMPT = """\
You are a Neo4j Cypher expert. Convert the user's natural language query into a
valid, read-only Cypher query for a personal knowledge graph.

Graph schema:
- (:Memory {{memory_id, tenant_id, content, created_at, is_valid, confidence}})
- (:Concept {{concept_id, tenant_id, name, type, first_seen, last_seen}})
- (:Source {{source_id, tenant_id, original_filename, file_type}})
- (:MetaDocument {{doc_id, tenant_id, title, generated_at}})
- (Memory)-[:EXTRACTED_FROM]->(Concept)
- (Memory)-[:EXTRACTED_FROM]->(Source)
- (Memory)-[:CONTRADICTS]->(Memory)
- (Memory)-[:RELATES_TO]->(Concept)
- (MetaDocument)-[:CONTAINS]->(Memory)

Rules:
- Read-only only: use MATCH, OPTIONAL MATCH, RETURN, ORDER BY, LIMIT.
- Never use CREATE, MERGE, SET, DELETE, REMOVE, DROP, or CALL procedures.
- Do NOT include a tenant_id filter — it will be added automatically.
- Use LIMIT {limit}.
- Primary node alias must be n. Neighbour alias must be m.
- Your RETURN clause MUST use exactly these column aliases:
    labels(n)[0] AS n_type, properties(n) AS n_props,
    type(r) AS r_type, properties(r) AS r_props,
    labels(m)[0] AS m_type, properties(m) AS m_props
- If the query cannot be answered from this schema, use this fallback:
    MATCH (n:Memory) OPTIONAL MATCH (n)-[r]-(m)
    RETURN labels(n)[0] AS n_type, properties(n) AS n_props,
           type(r) AS r_type, properties(r) AS r_props,
           labels(m)[0] AS m_type, properties(m) AS m_props
    LIMIT {limit}
- Return ONLY the Cypher query. No explanation. No markdown. No backticks.

User query:
<user_query>{query}</user_query>
"""

_FIRST_NODE_VAR: re.Pattern[str] = re.compile(
    r"MATCH\s*\(([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE
)


def inject_tenant_filter(cypher: str) -> str:
    """Inject WHERE n.tenant_id = $tenant_id into the first MATCH clause.

    RULE 11: inserts the Cypher parameter placeholder ``$tenant_id``, never
    the literal tenant_id value. The actual value is passed to run_query()
    as a keyword argument so it travels through the Neo4j parameterised
    execution path.

    Two cases:
    - No WHERE: inserts ``WHERE <var>.tenant_id = $tenant_id`` after first
      node pattern.
    - WHERE already present: prepends ``<var>.tenant_id = $tenant_id AND ``
      to the first WHERE clause.
    """
    # If $tenant_id already in the query, assume LLM placed it correctly
    if "$tenant_id" in cypher:
        return cypher

    var_match = _FIRST_NODE_VAR.search(cypher)
    var = var_match.group(1) if var_match else "n"

    if re.search(r"\bWHERE\b", cypher, re.IGNORECASE):
        return re.sub(
            r"\bWHERE\b",
            f"WHERE {var}.tenant_id = $tenant_id AND ",
            cypher,
            count=1,
            flags=re.IGNORECASE,
        )
    return re.sub(
        r"(MATCH\s*\([^)]*\))",
        rf"\1 WHERE {var}.tenant_id = $tenant_id",
        cypher,
        count=1,
        flags=re.IGNORECASE,
    )


class GraphQueryService(BaseService):
    """Text-to-Cypher service for natural language graph queries (STORY-029).

    Adapters are injection-optional — lazy-created in production, mocked in tests.
    """

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
        neo4j_adapter: Neo4jAdapter | None = None,
    ) -> None:
        self._llm_router = llm_router
        self._neo4j = neo4j_adapter

    def _get_llm_router(self) -> LLMRouter:
        if self._llm_router is None:
            self._llm_router = LLMRouter()
        return self._llm_router

    def _get_neo4j(self) -> Neo4jAdapter:
        if self._neo4j is None:
            self._neo4j = Neo4jAdapter()
        return self._neo4j

    async def execute_nl_query(
        self,
        query: str,
        tenant_id: str,
        profile_id: str | None,  # noqa: ARG002
        limit: int,
    ) -> GraphQueryResponse:
        """Execute a natural language query via Text-to-Cypher.

        Flow:
          1. Generate Cypher via LLMRouter("cypher_generation") — plain text
          2. Safety check — reject write operations (AC-3)
          3. Inject tenant filter as Cypher param ref (AC-4, RULE 11)
          4. Execute against Neo4j, measure wall-clock time (AC-7)
          5. Parse rows with GraphService._rows_to_graph_response() (AC-5)
          6. Build explanation (AC-6, AC-9)
        """
        log = logger.bind(tenant_id=tenant_id, nl_query=query)
        log.info("graph_query.started")

        safe_limit = min(limit, 50)  # AC-10: hard cap regardless of input

        # Step 1: Generate Cypher — AC-2
        # response_format intentionally omitted: Cypher is plain text, not JSON
        prompt = CYPHER_GENERATION_PROMPT.format(query=query, limit=safe_limit)
        raw_cypher = await self._get_llm_router().complete(
            task="cypher_generation",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            tenant_id=tenant_id,
        )
        raw_cypher = raw_cypher.strip()
        log.info("graph_query.cypher_generated", cypher=raw_cypher)

        # Step 2: Safety check — AC-3 (fail before Neo4j touch)
        if CYPHER_WRITE_KEYWORDS.search(raw_cypher):
            log.warning("graph_query.unsafe_cypher_rejected", cypher=raw_cypher)
            raise_422(ErrorCode.UNSAFE_QUERY, "Query must be read-only")

        # Step 3: Inject tenant filter as parameter ref — AC-4, RULE 11
        safe_cypher = inject_tenant_filter(raw_cypher)

        # Step 4: Execute against Neo4j — AC-7 (measure Neo4j time only)
        start_ns = time.monotonic_ns()
        rows = await self._get_neo4j().run_query(
            safe_cypher,
            tenant_id=tenant_id,
        )
        query_time_ms = int((time.monotonic_ns() - start_ns) / 1_000_000)
        log.info("graph_query.executed", row_count=len(rows), query_time_ms=query_time_ms)

        # Step 5: Parse rows — AC-5 (reuse existing static helper)
        graph_response: GraphResponse = GraphService._rows_to_graph_response(
            rows, node_types=None
        )

        # Step 6: Explanation — AC-6, AC-9
        node_count = len(graph_response.nodes)
        if node_count:
            explanation = (
                f"Found {node_count} node{'s' if node_count != 1 else ''} "
                f"matching your query."
            )
        else:
            explanation = "No memories found matching your query."

        log.info(
            "graph_query.completed",
            node_count=node_count,
            edge_count=len(graph_response.edges),
        )
        return GraphQueryResponse(
            cypher=safe_cypher,
            results=graph_response,
            explanation=explanation,
            query_time_ms=query_time_ms,
        )

    def cleanup(self) -> None:
        if self._neo4j:
            self._neo4j.cleanup()
