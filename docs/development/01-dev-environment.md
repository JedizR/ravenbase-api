# Development — 01. Dev Environment Setup

> **Cross-references:** `development/00-project-structure.md` | `development/02-coding-standards.md`
>
> **AGENT NOTE:** This is the setup guide for local development. Run these commands once to get a working environment.

---

## Prerequisites

```bash
# Required tools (install manually before setup):
# - Python 3.12+         → pyenv install 3.12.3
# - uv                   → curl -LsSf https://astral.sh/uv/install.sh | sh
# - Node.js 20+          → nvm install 20
# - Docker Desktop       → https://docker.com/products/docker-desktop
# - Git

# Verify:
python --version     # 3.12.x
uv --version         # 0.x.x
node --version       # v20.x.x
docker --version     # Docker version 24+
```

---

## Backend Setup (ravenbase-api)

```bash
# Clone and enter
git clone git@github.com:jediwannabe/ravenbase-api.git
cd ravenbase-api

# Install Python dependencies (creates .venv automatically)
uv sync --dev

# Install pre-commit hooks (runs ruff + pyright on every commit)
uv run pre-commit install

# Copy environment template
cp .envs/.env.example .envs/.env.dev

# Fill in required secrets in .envs/.env.dev:
# DATABASE_URL, REDIS_URL, CLERK_SECRET_KEY, OPENAI_API_KEY,
# ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
# QDRANT_URL, NEO4J_URI, NEO4J_PASSWORD

# Start local infrastructure (PostgreSQL + Redis only — Qdrant+Neo4j are cloud)
docker-compose up -d postgres redis

# Run database migrations
uv run alembic upgrade head

# Seed test data
uv run python scripts/seed_dev_data.py

# Start API server
uv run uvicorn src.api.main:app --reload --port 8000

# In separate terminal: Start ARQ worker
uv run arq src.workers.main.WorkerSettings --watch src/

# Verify health:
curl http://localhost:8000/health
```

---

## Frontend Setup (ravenbase-web)

```bash
# Clone and enter
git clone git@github.com:jediwannabe/ravenbase-web.git
cd ravenbase-web

# Install dependencies
npm install

# Install Playwright browsers (one-time — required for E2E tests):
npx playwright install chromium

# Copy environment template
cp .env.local.example .env.local

# Fill in:
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
# CLERK_SECRET_KEY=sk_test_...

# Generate TypeScript API client from backend OpenAPI spec
# (backend must be running)
npm run generate-client

# Start dev server
npm run dev
# → http://localhost:3000
```

---

## Full Stack Local (docker-compose.local.yml)

Place this in a parent `workspace/` directory:

```yaml
# workspace/docker-compose.local.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ravenbase_dev
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "dev"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333", "6334:6334"]
    volumes: ["qdrant_storage:/qdrant/storage"]

  backend:
    build:
      context: ./ravenbase-api
      dockerfile: Dockerfile.api
    ports: ["8000:8000"]
    volumes: ["./ravenbase-api/src:/app/src"]
    env_file: ./ravenbase-api/.envs/.env.dev
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_started}
    environment:
      QDRANT_URL: http://qdrant:6333

  worker:
    build:
      context: ./ravenbase-api
      dockerfile: Dockerfile.worker
    volumes: ["./ravenbase-api/src:/app/src"]
    env_file: ./ravenbase-api/.envs/.env.dev
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_started}
    environment:
      QDRANT_URL: http://qdrant:6333
    command: arq src.workers.main.WorkerSettings

  frontend:
    image: node:20-alpine
    working_dir: /app
    ports: ["3000:3000"]
    volumes:
      - ./ravenbase-web:/app
      - /app/node_modules
    command: sh -c "npm install && npm run dev"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
      CHOKIDAR_USEPOLLING: "true"    # Required for Docker file watching on macOS
      WATCHPACK_POLLING: "true"
    depends_on: [backend]

volumes:
  qdrant_storage:
```

```bash
# Start everything:
cd workspace/
docker-compose -f docker-compose.local.yml up

# Stop (never add -v — that deletes the postgres volume):
docker-compose -f docker-compose.local.yml down
```

---

## Environment Variables Reference

### Backend (`.envs/.env.dev`)

```bash
# ─── Database ───────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5432/ravenbase_dev

# ─── Redis ──────────────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ─── Authentication ─────────────────────────────────────────────────
CLERK_SECRET_KEY=sk_test_...         # From Clerk dashboard → API Keys

# ─── AI APIs ────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...                # For text-embedding-3-small
ANTHROPIC_API_KEY=sk-ant-...         # For Claude Haiku + Sonnet
GEMINI_API_KEY=                      # Google Gemini — optional for local dev (tasks fall back to Claude Haiku)

# ─── Vector Store ───────────────────────────────────────────────────
QDRANT_URL=http://localhost:6333     # Docker local / Qdrant Cloud URL
QDRANT_API_KEY=                      # Empty for local Docker

# ─── Graph Database ─────────────────────────────────────────────────
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io   # AuraDB connection string
NEO4J_USER=neo4j
NEO4J_PASSWORD=                      # From AuraDB dashboard

# ─── File Storage ───────────────────────────────────────────────────
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...     # Service role (backend only, never frontend)
STORAGE_BUCKET=ravenbase-sources

# ─── App Config ─────────────────────────────────────────────────────
APP_ENV=development
CONFLICT_SIMILARITY_THRESHOLD=0.87
MAX_CONCURRENT_INGEST_JOBS=3
ENABLE_PII_MASKING=false             # Disable in dev for faster iteration

# ─── Optional ───────────────────────────────────────────────────────
SENTRY_DSN=                          # Leave empty in dev
RESEND_API_KEY=             # Transactional email. Get from resend.com. Leave blank to skip.
```

### Frontend (`.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...         # Same key as backend
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ... # Anon key (safe to expose)
NEXT_PUBLIC_POSTHOG_KEY=             # Optional: product analytics
# No RESEND_API_KEY in web .env.local — emails are sent from the API backend only
# Add RESEND_API_KEY to ravenbase-api/.envs/.env.dev instead
```

---

## Makefile Commands (Backend)

```bash
make dev-up        # Start postgres + redis in Docker
make dev-down      # Stop Docker services
make migrate       # Create + apply Alembic migration (MSG="description")
make db-upgrade    # Apply pending migrations only
make seed          # Run seed script with test data
make lint-fix      # Auto-fix ruff lint issues
make format        # Format with ruff
make quality       # Run ruff + pyright (must pass 0 errors before commit)
make test          # Run all tests with coverage
make ci-local      # make quality + make test (run before PR)
make worker        # Start ARQ worker with hot reload
```

---

## OpenAPI Client Regeneration (Frontend)

Run this whenever backend API schema changes:

```bash
# In ravenbase-web/
npm run generate-client

# This runs:
# openapi-ts --input http://localhost:8000/openapi.json
#            --output src/lib/api-client
#            --client axios

# Commit the generated files:
git add src/lib/api-client/
git commit -m "chore: regenerate API client from OpenAPI spec"
```
