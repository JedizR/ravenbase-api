# tests/integration/api/test_database_connectivity.py
"""
Integration test: verifies that Alembic migrations have been applied and all
expected tables exist in the PostgreSQL database.

Requires: running PostgreSQL (via docker compose up -d postgres).
Run with: uv run pytest tests/integration/api/test_database_connectivity.py -v
"""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import settings

EXPECTED_TABLES = {
    "users",
    "system_profiles",
    "sources",
    "source_authority_weights",
    "conflicts",
    "meta_documents",
    "credit_transactions",
    "job_statuses",
}


@pytest.mark.asyncio
async def test_database_connectivity() -> None:
    """DB is reachable and returns a result."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_all_expected_tables_exist() -> None:
    """All 8 tables from the initial migration are present."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        table_names = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )
    await engine.dispose()

    missing = EXPECTED_TABLES - table_names
    assert not missing, f"Missing tables after migration: {missing}"


@pytest.mark.asyncio
async def test_composite_indexes_exist() -> None:
    """Critical composite indexes are present for query performance."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
                "AND indexname IN ("
                "'idx_sources_user_ingested', "
                "'idx_conflicts_user_status_created'"
                ")"
            )
        )
        found_indexes = {row[0] for row in result.fetchall()}
    await engine.dispose()

    expected_indexes = {"idx_sources_user_ingested", "idx_conflicts_user_status_created"}
    missing = expected_indexes - found_indexes
    assert not missing, f"Missing composite indexes: {missing}"
