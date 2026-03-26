import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    from src.api.main import app  # noqa: PLC0415

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_qdrant():
    from unittest.mock import AsyncMock, MagicMock  # noqa: PLC0415

    from src.adapters.qdrant_adapter import QdrantAdapter  # noqa: PLC0415

    adapter = MagicMock(spec=QdrantAdapter)
    adapter.search = AsyncMock(return_value=[])
    adapter.upsert = AsyncMock()
    adapter.delete_by_filter = AsyncMock()
    adapter.count = AsyncMock(return_value=0)
    adapter.verify_connectivity = AsyncMock(return_value=True)
    return adapter


@pytest.fixture
def mock_neo4j():
    from unittest.mock import AsyncMock, MagicMock  # noqa: PLC0415

    from src.adapters.neo4j_adapter import Neo4jAdapter  # noqa: PLC0415

    adapter = MagicMock(spec=Neo4jAdapter)
    adapter.run_query = AsyncMock(return_value=[])
    adapter.write_nodes = AsyncMock()
    adapter.write_relationships = AsyncMock()
    adapter.verify_connectivity = AsyncMock(return_value=True)
    return adapter
