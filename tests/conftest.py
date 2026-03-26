import os

import pytest
from httpx import ASGITransport, AsyncClient

_LOCAL_DB_URL = "postgresql+asyncpg://ravenbase:ravenbase@localhost:5432/ravenbase"


@pytest.fixture(autouse=True, scope="session")
def _override_database_url():
    """Ensure all tests use local docker postgres, not any cloud URL from .env.dev.

    test_database_connectivity.py imports `settings` at module level (a cached
    singleton), so we must mutate the singleton directly in addition to patching
    os.environ for fixtures that call get_settings() at runtime.
    """
    import src.core.config as _cfg  # noqa: PLC0415

    original_env = os.environ.get("DATABASE_URL")
    original_url = _cfg.settings.DATABASE_URL

    os.environ["DATABASE_URL"] = _LOCAL_DB_URL
    _cfg.settings.DATABASE_URL = _LOCAL_DB_URL
    _cfg.get_settings.cache_clear()

    yield

    _cfg.settings.DATABASE_URL = original_url
    if original_env is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original_env
    _cfg.get_settings.cache_clear()


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
