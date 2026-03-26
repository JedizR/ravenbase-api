# tests/integration/api/test_health_endpoint.py
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_healthy_with_all_checks(client: AsyncClient, mocker) -> None:
    # Qdrant and Neo4j are not in the test docker-compose — mock their connectivity
    mocker.patch(
        "src.api.routes.health.QdrantAdapter.verify_connectivity",
        new=AsyncMock(return_value=True),
    )
    mocker.patch(
        "src.api.routes.health.Neo4jAdapter.verify_connectivity",
        new=AsyncMock(return_value=True),
    )

    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "checks" in data
    assert data["checks"]["qdrant"] == "ok"
    assert data["checks"]["neo4j"] == "ok"
    # postgres and redis are available in test docker-compose
    assert data["checks"]["postgresql"] in ("ok", "error")
    assert data["checks"]["redis"] in ("ok", "error")


@pytest.mark.asyncio
async def test_health_reports_degraded_when_service_down(client: AsyncClient, mocker) -> None:
    mocker.patch(
        "src.api.routes.health.QdrantAdapter.verify_connectivity",
        new=AsyncMock(return_value=False),
    )
    mocker.patch(
        "src.api.routes.health.Neo4jAdapter.verify_connectivity",
        new=AsyncMock(return_value=True),
    )

    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["qdrant"] == "error"
    assert data["checks"]["neo4j"] == "ok"
