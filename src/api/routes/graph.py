# src/api/routes/graph.py
from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.schemas.graph import GraphQueryRequest, GraphQueryResponse, GraphResponse
from src.services.credit_service import CreditService
from src.services.graph_query_service import GraphQueryService
from src.services.graph_service import GraphService

router = APIRouter(prefix="/v1/graph", tags=["graph"])


@router.get("/nodes", response_model=GraphResponse)
async def get_graph_nodes(
    profile_id: str | None = Query(default=None),
    node_types: str | None = Query(
        default=None, description="Comma-separated node types, e.g. Concept,Memory"
    ),
    limit: int = Query(default=200, ge=1, le=1000),
    user: dict = Depends(require_user),  # noqa: B008
) -> GraphResponse:
    """Return all graph nodes and edges for the authenticated user.

    Empty graph returns {nodes: [], edges: []} — never 404.
    tenant_id is extracted from JWT only, never from request params (RULE 2).
    """
    node_types_list: list[str] | None = None
    if node_types:
        node_types_list = [t.strip() for t in node_types.split(",") if t.strip()]

    with GraphService() as svc:
        return await svc.get_nodes_for_explorer(
            tenant_id=user["user_id"],
            profile_id=profile_id,
            node_types=node_types_list,
            limit=limit,
        )


@router.get("/neighborhood/{node_id}", response_model=GraphResponse)
async def get_graph_neighborhood(
    node_id: str,
    hops: int = Query(default=2, ge=1, le=5),
    limit: int = Query(default=50, ge=1, le=500),
    user: dict = Depends(require_user),  # noqa: B008
) -> GraphResponse:
    """Return the N-hop neighborhood subgraph centered on a specific node.

    tenant_id is extracted from JWT only (RULE 2).
    """
    with GraphService() as svc:
        return await svc.get_neighborhood(
            node_id=node_id,
            tenant_id=user["user_id"],
            hops=hops,
            limit=limit,
        )


_GRAPH_QUERY_CREDITS = 2


@router.post("/query", response_model=GraphQueryResponse)
async def natural_language_graph_query(
    body: GraphQueryRequest,
    user: dict = Depends(require_user),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> GraphQueryResponse:
    """Convert a natural language question into Cypher and execute against the graph.

    Returns cypher, results (nodes + edges), explanation, and query_time_ms.
    Raises 402 if insufficient credits (checked before LLM call — AC-8).
    Raises 422 UNSAFE_QUERY if generated Cypher contains write operations (AC-3).
    tenant_id is extracted from JWT only — never from request body (RULE 2).
    """
    # AC-8: deduct credits atomically before LLM call; raises 402 if insufficient
    await CreditService().deduct(
        db=db,
        user_id=user["user_id"],
        amount=_GRAPH_QUERY_CREDITS,
        operation="graph_query",
    )

    with GraphQueryService() as svc:
        return await svc.execute_nl_query(
            query=body.query,
            tenant_id=user["user_id"],
            profile_id=body.profile_id,
            limit=body.limit,
        )
