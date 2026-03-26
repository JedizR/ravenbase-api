# src/api/routes/graph.py
from fastapi import APIRouter, Depends, Query

from src.api.dependencies.auth import require_user
from src.schemas.graph import GraphResponse
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
