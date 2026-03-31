from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".envs/.env.dev",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://ravenbase:ravenbase@localhost:5432/ravenbase"
    REDIS_URL: str = "redis://localhost:6379"

    CLERK_SECRET_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""
    CLERK_FRONTEND_API: str = ""

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""

    NEO4J_URI: str = ""
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    STORAGE_BUCKET: str = "ravenbase-sources"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = Field(
        default="",
        description="Stripe webhook signing secret (whsec_...). Required in production — set STRIPE_WEBHOOK_SECRET env var.",
    )
    STRIPE_PRO_MONTHLY_PRICE_ID: str = Field(
        default="",
        description="Stripe Price ID for Pro monthly ($15/mo). Starts with price_",
    )
    STRIPE_PRO_ANNUAL_PRICE_ID: str = Field(
        default="",
        description="Stripe Price ID for Pro annual ($144/yr = $12/mo). Starts with price_",
    )
    STRIPE_TEAM_MONTHLY_PRICE_ID: str = Field(
        default="",
        description="Stripe Price ID for Team monthly ($49/mo). Starts with price_",
    )
    STRIPE_TEAM_ANNUAL_PRICE_ID: str = Field(
        default="",
        description="Stripe Price ID for Team annual ($468/yr = $39/mo). Starts with price_",
    )
    APP_BASE_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend base URL. Used to construct Stripe checkout success/cancel URLs.",
    )
    RESEND_API_KEY: str = ""
    RESEND_WEBHOOK_SECRET: str = ""

    CLOUDFLARE_ORIGIN_SECRET: str = ""

    ENABLE_PII_MASKING: bool = False
    CONFLICT_SIMILARITY_THRESHOLD: float = 0.87
    MAX_CONCURRENT_INGEST_JOBS: int = 3
    MAX_DAILY_LLM_SPEND_USD: float = 50.0
    ADMIN_USER_IDS: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
