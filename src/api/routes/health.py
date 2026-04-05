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


@router.get("/health/debug")
async def health_debug() -> dict:
    """Detailed diagnostic endpoint — shows errors and config status."""
    settings = get_settings()
    log = get_logger()

    results: dict = {}

    # 1. Neo4j — detailed
    try:
        adapter = Neo4jAdapter()
        ok = await adapter.verify_connectivity()
        if ok:
            # Try a simple query
            rows = await adapter.run_query("RETURN 1 AS n")
            results["neo4j"] = {"status": "ok", "test_query": "passed", "uri": settings.NEO4J_URI[:40] + "..."}
        else:
            results["neo4j"] = {"status": "unreachable", "uri": settings.NEO4J_URI[:40] + "...", "user": settings.NEO4J_USER}
        adapter.cleanup()
    except Exception as exc:
        results["neo4j"] = {"status": "error", "error": str(exc)[:300], "uri": settings.NEO4J_URI[:40] + "...", "user": settings.NEO4J_USER}

    # 2. Qdrant — check collection
    try:
        qa = QdrantAdapter()
        ok = await qa.verify_connectivity()
        if ok:
            await qa.ensure_collection()
            results["qdrant"] = {"status": "ok", "collection": qa.COLLECTION_NAME}
        else:
            results["qdrant"] = {"status": "unreachable"}
        qa.cleanup()
    except Exception as exc:
        results["qdrant"] = {"status": "error", "error": str(exc)[:300]}

    # 3. LLM — test entity extraction model
    try:
        import litellm  # noqa: PLC0415
        resp = await litellm.acompletion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        results["gemini"] = {"status": "ok", "response": resp.choices[0].message.content[:50]}
    except Exception as exc:
        results["gemini"] = {"status": "error", "error": str(exc)[:300]}

    # 4. Anthropic
    results["anthropic_key_set"] = bool(settings.ANTHROPIC_API_KEY)
    results["gemini_key_set"] = bool(settings.GEMINI_API_KEY)
    results["openai_key_set"] = bool(settings.OPENAI_API_KEY)

    # 5. Config summary
    results["neo4j_uri_set"] = bool(settings.NEO4J_URI)
    results["neo4j_user"] = settings.NEO4J_USER

    return results


@router.post("/health/test-graph-extraction")
async def test_graph_extraction(
    source_id: str = "",
) -> dict:
    """Manually run graph extraction for a source_id — for debugging only.

    Runs in the API process (not worker), so we can see if it succeeds
    when all services are confirmed connected via /health/debug.
    """
    log = get_logger()
    if not source_id:
        return {"error": "Pass ?source_id=<uuid> of an uploaded source"}

    try:
        # 1. Check Qdrant for chunks
        qa = QdrantAdapter()
        await qa.ensure_collection()
        # Use scroll to find chunks for this source
        chunks = await qa.scroll_by_source(source_id, tenant_id="")
        if not chunks:
            # Try without tenant filter — just check if source exists
            return {"error": f"No chunks found in Qdrant for source_id={source_id}", "hint": "Upload a file first"}

        tenant_id = chunks[0].get("tenant_id", "")
        log.info("test_graph.chunks_found", count=len(chunks), tenant_id=tenant_id)

        # 2. Run graph extraction
        from src.services.graph_service import GraphService  # noqa: PLC0415
        svc = GraphService()
        stats = await svc.extract_and_write(
            source_id=source_id,
            tenant_id=tenant_id,
        )
        return {"status": "ok", "chunks_found": len(chunks), "tenant_id": tenant_id, **stats}
    except Exception as exc:
        log.error("test_graph.failed", error=str(exc), exc_info=True)
        return {"status": "error", "error": str(exc)[:500]}
