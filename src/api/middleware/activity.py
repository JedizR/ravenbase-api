# src/api/middleware/activity.py
"""ActivityTrackingMiddleware: debounced last_active_at updates (STORY-037).

After each authenticated non-skip request, checks a Redis key (TTL=24h).
On cache miss, fires asyncio.create_task() to update last_active_at in PG.
NEVER awaited — fire-and-forget. Errors are logged and swallowed.
"""

import asyncio
from datetime import datetime

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

SKIP_PATHS = {
    "/health",
    "/metrics",
    "/webhooks/clerk",
    "/webhooks/stripe",
    "/webhooks/resend",
    "/v1/ingest/stream",
}

_DEBOUNCE_TTL = 86400  # 24 hours


async def _update_last_active(redis_client, db_factory, user_id: str) -> None:
    """Background task: write last_active_at to PostgreSQL, then set Redis key.

    Redis key is set AFTER successful DB write so a failed write retries
    on the next request (no stale debounce key on failure).
    """
    log = logger.bind(tenant_id=user_id, action="activity_update")
    try:
        from sqlalchemy import text  # noqa: PLC0415

        now = datetime.utcnow()
        async with db_factory() as db:
            await db.execute(
                text("UPDATE users SET last_active_at = :ts WHERE id = :uid"),
                {"ts": now, "uid": user_id},
            )
            await db.commit()
        await redis_client.set(f"activity:{user_id}", "1", ex=_DEBOUNCE_TTL)
        log.info("activity.updated", last_active_at=now.isoformat())
    except Exception as exc:
        log.error("activity.update_failed", error=str(exc))


class ActivityTrackingMiddleware(BaseHTTPMiddleware):
    """Debounced last_active_at updater.

    Requires app.state.redis (redis.asyncio.Redis).
    db_factory is injected for tests; defaults to async_session_factory in prod.
    """

    def __init__(self, app, db_factory=None) -> None:
        super().__init__(app)
        self._db_factory = db_factory

    def _get_db_factory(self):
        if self._db_factory is not None:
            return self._db_factory
        from src.api.dependencies.db import async_session_factory  # noqa: PLC0415

        return async_session_factory

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Skip unauthenticated requests and noisy paths
        user_id: str | None = getattr(request.state, "user_id", None)
        if not user_id or request.url.path in SKIP_PATHS:
            return response

        try:
            redis_client = request.app.state.redis
            cache_key = f"activity:{user_id}"
            already_tracked = await redis_client.exists(cache_key)
            if not already_tracked:
                asyncio.create_task(
                    _update_last_active(redis_client, self._get_db_factory(), user_id)
                )
        except Exception as exc:
            logger.error("activity.middleware_error", error=str(exc))

        return response
