# src/api/routes/health.py
import asyncio

import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from structlog import get_logger

from src.adapters.neo4j_adapter import Neo4jAdapter
from src.adapters.qdrant_adapter import QdrantAdapter
from src.core.config import get_settings

router = APIRouter(tags=["health"])


async def _check_postgresql() -> str:
    # TODO: replace with app.state.engine once DB session lifespan is wired
    try:
        engine = create_async_engine(get_settings().DATABASE_URL, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return "ok"
    except Exception as exc:
        get_logger().warning("health.postgresql_check_failed", error=str(exc))
        return "error"


async def _check_redis() -> str:
    try:
        client = aioredis.from_url(get_settings().REDIS_URL, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return "ok"
    except Exception as exc:
        get_logger().warning("health.redis_check_failed", error=str(exc))
        return "error"


async def _check_qdrant() -> str:
    adapter = QdrantAdapter()
    try:
        ok = await adapter.verify_connectivity()
        return "ok" if ok else "error"
    finally:
        if adapter._client is not None:
            await adapter._client.close()
        adapter.cleanup()


async def _check_neo4j() -> str:
    adapter = Neo4jAdapter()
    try:
        ok = await adapter.verify_connectivity()
        return "ok" if ok else "error"
    finally:
        if adapter._driver is not None:
            await adapter._driver.close()
        adapter.cleanup()


@router.get("/health")
async def health_check() -> dict:
    postgresql, redis_status, qdrant, neo4j = await asyncio.gather(
        _check_postgresql(),
        _check_redis(),
        _check_qdrant(),
        _check_neo4j(),
    )
    checks = {
        "postgresql": postgresql,
        "redis": redis_status,
        "qdrant": qdrant,
        "neo4j": neo4j,
    }
    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}
