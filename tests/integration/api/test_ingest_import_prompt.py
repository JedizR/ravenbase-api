# tests/integration/api/test_ingest_import_prompt.py
"""
Integration tests for GET /v1/ingest/import-prompt.

Run with: uv run pytest tests/integration/api/test_ingest_import_prompt.py -v
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.auth import require_user
from src.api.main import app

TEST_TENANT_ID = str(uuid.uuid4())
TEST_PROFILE_ID = str(uuid.uuid4())


@pytest.fixture
async def import_prompt_client():
    """Client with mocked auth. Neo4jAdapter is patched per-test."""
    app.dependency_overrides[require_user] = lambda: {
        "user_id": TEST_TENANT_ID,
        "email": "test@example.com",
        "tier": "free",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(require_user, None)


@pytest.mark.asyncio
async def test_with_concepts_returns_personalized_prompt(
    import_prompt_client: AsyncClient,
) -> None:
    """When tenant has concepts, prompt_text mentions them and detected_concepts is populated."""
    mock_adapter = MagicMock()
    mock_adapter.get_concepts_for_tenant = AsyncMock(
        return_value=["Python", "FastAPI", "Neo4j"]
    )

    with patch(
        "src.services.ingestion_service.Neo4jAdapter", return_value=mock_adapter
    ):
        response = await import_prompt_client.get("/v1/ingest/import-prompt")

    assert response.status_code == 200
    data = response.json()
    assert data["detected_concepts"] == ["Python", "FastAPI", "Neo4j"]
    assert "Python" in data["prompt_text"]
    assert "FastAPI" in data["prompt_text"]
    assert "Neo4j" in data["prompt_text"]
    assert isinstance(data["prompt_text"], str)
    assert len(data["prompt_text"]) > 0


@pytest.mark.asyncio
async def test_no_concepts_returns_generic_prompt(
    import_prompt_client: AsyncClient,
) -> None:
    """New user with zero concepts gets generic prompt and empty detected_concepts list."""
    mock_adapter = MagicMock()
    mock_adapter.get_concepts_for_tenant = AsyncMock(return_value=[])

    with patch(
        "src.services.ingestion_service.Neo4jAdapter", return_value=mock_adapter
    ):
        response = await import_prompt_client.get("/v1/ingest/import-prompt")

    assert response.status_code == 200
    data = response.json()
    assert data["detected_concepts"] == []
    assert isinstance(data["prompt_text"], str)
    assert len(data["prompt_text"]) > 0


@pytest.mark.asyncio
async def test_profile_id_param_passed_to_neo4j(
    import_prompt_client: AsyncClient,
) -> None:
    """profile_id query param is forwarded to Neo4jAdapter.get_concepts_for_tenant."""
    mock_adapter = MagicMock()
    mock_adapter.get_concepts_for_tenant = AsyncMock(return_value=["TypeScript"])

    with patch(
        "src.services.ingestion_service.Neo4jAdapter", return_value=mock_adapter
    ):
        response = await import_prompt_client.get(
            f"/v1/ingest/import-prompt?profile_id={TEST_PROFILE_ID}"
        )

    assert response.status_code == 200
    mock_adapter.get_concepts_for_tenant.assert_called_once_with(
        tenant_id=TEST_TENANT_ID,
        profile_id=TEST_PROFILE_ID,
    )


@pytest.mark.asyncio
async def test_unauthenticated_returns_401() -> None:
    """No auth header → 401 MISSING_AUTH."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/ingest/import-prompt")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "MISSING_AUTH"
