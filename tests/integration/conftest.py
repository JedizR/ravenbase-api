import os

import pytest

from src.core.config import get_settings

LOCAL_DB_URL = "postgresql+asyncpg://ravenbase:ravenbase@localhost:5432/ravenbase"


@pytest.fixture(autouse=True, scope="session")
def override_db_url_for_integration_tests():
    """Override DATABASE_URL to use local docker-compose postgres for integration tests.

    The .env.dev file may point DATABASE_URL at a remote Supabase instance.
    Integration tests run against the local docker-compose postgres instead.
    """
    key = "DATABASE_URL"
    original = os.environ.get(key)
    os.environ[key] = LOCAL_DB_URL
    get_settings.cache_clear()
    yield
    if original is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = original
    get_settings.cache_clear()
