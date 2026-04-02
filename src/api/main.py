from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.activity import ActivityTrackingMiddleware
from src.api.routes import (
    account,
    admin,
    billing,
    chat,
    conflict,
    credits,
    graph,
    health,
    ingest,
    metadoc,
    profiles,
    webhooks,
)
from src.core.config import settings
from src.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    yield
    await app.state.arq_pool.close()
    await app.state.redis.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ravenbase API",
        version="0.1.0",
        lifespan=lifespan,
    )

    origins = (
        ["http://localhost:3000"]
        if settings.APP_ENV == "development"
        else ["https://ravenbase.app"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ActivityTrackingMiddleware)

    app.include_router(health.router)
    app.include_router(admin.router)
    app.include_router(ingest.router)
    app.include_router(graph.router)
    app.include_router(conflict.router)
    app.include_router(metadoc.router)
    app.include_router(credits.router)
    app.include_router(billing.router)
    app.include_router(webhooks.router)
    app.include_router(account.router)
    app.include_router(account.users_router)
    app.include_router(chat.router)
    app.include_router(profiles.router)
    return app


app = create_app()
