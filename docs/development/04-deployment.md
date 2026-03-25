# Development — 04. Deployment

> **Cross-references:** `development/05-operations.md` | `architecture/00-system-overview.md`

---

## Deployment Architecture

```
GitHub → PR → CI passes → merge to main
  │
  ├─► Vercel (frontend)    auto-deploys on push to main
  └─► Railway (backend)    auto-deploys on push to main
        ├── API service   (Dockerfile.api)
        └── Worker service (Dockerfile.worker)
```

---

## Pre-Deployment: Cloudflare Setup (Do Before Going Live)

```
1. Create free Cloudflare account → Add site → Enter your domain
2. Update nameservers at your registrar to Cloudflare's nameservers
3. Security → WAF → Enable "Cloudflare Managed Ruleset"
4. Security → Bots → Enable "Bot Fight Mode"
5. Security → Rate Limiting → URI: /*, Rate: 100 req/10s per IP, Action: Block
6. Rules → Transform Rules → Add request header: X-CF-Secret = <32-char hex>
7. Railway env: CLOUDFLARE_ORIGIN_SECRET=<same value>
```

---

## Backend: Railway

### Initial Setup (one-time)

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Link to project
railway link

# Set environment variables
railway variables set DATABASE_URL=...
railway variables set REDIS_URL=...
railway variables set CLERK_SECRET_KEY=...
railway variables set OPENAI_API_KEY=...
railway variables set ANTHROPIC_API_KEY=...
railway variables set SUPABASE_URL=...
railway variables set SUPABASE_SERVICE_ROLE_KEY=...
railway variables set QDRANT_URL=...
railway variables set QDRANT_API_KEY=...
railway variables set NEO4J_URI=...
railway variables set NEO4J_USER=neo4j
railway variables set NEO4J_PASSWORD=...
railway variables set APP_ENV=production
railway variables set ENABLE_PII_MASKING=true
railway variables set SENTRY_DSN=...
```

### Railway Services Configuration

**Service 1: API** (`Dockerfile.api`)
```
Start command: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
Health check: GET /health
Deploy trigger: Push to main
```

**Service 2: Worker** (`Dockerfile.worker`)
```
Start command: arq src.workers.main.WorkerSettings
Health check: (none — ARQ provides health_check_key in Redis)
Deploy trigger: Push to main
```

### Database Migration on Deploy

Add a pre-deploy command to Railway:
```
uv run alembic upgrade head
```

This runs migrations before the new API version starts handling requests.

### GitHub Actions CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
    paths-ignore:
      - "docs/**"
      - ".bmad/**"
      - "**.md"

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: "ravenbase-api"
```

---

## Frontend: Vercel

### Initial Setup (one-time)

```bash
npm install -g vercel
cd ravenbase-web
vercel                    # follow prompts, link to project

# Set environment variables in Vercel dashboard:
vercel env add NEXT_PUBLIC_API_URL production
vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY production
vercel env add CLERK_SECRET_KEY production
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
```

### Vercel Configuration

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["sin1"],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self' 'unsafe-inline' https://*.clerk.accounts.dev; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self' https://api.ravenbase.app https://*.clerk.accounts.dev; frame-ancestors 'none';" },
        { "key": "Permissions-Policy", "value": "geolocation=(), microphone=(), camera=(), payment=()" }
      ]
    }
  ]
}
```

Auto-deploys on push to main. Preview deployments on PRs.

---

## Dockerfiles

### `Dockerfile.api`

```dockerfile
FROM python:3.12.3-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev

FROM python:3.12.3-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### `Dockerfile.worker`

```dockerfile
FROM python:3.12.3-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev

FROM python:3.12.3-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
# Docling needs system libs
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*
CMD ["arq", "src.workers.main.WorkerSettings"]
```

---

## Rollback Procedure

```bash
# 1. Identify last good deploy SHA
GOOD_SHA=abc1234   # from Railway deploy history

# 2. Railway: redeploy from previous image
railway service rollback --deployment $GOOD_SHA

# 3. If migration was included, downgrade:
railway run uv run alembic downgrade -1
# ⚠️ Only for destructive migrations. Additive migrations (new nullable columns) are safe to leave.

# 4. Verify health:
curl https://api.ravenbase.app/health

# 5. Post-mortem (save to docs/incidents/YYYY-MM-DD.md):
# - What broke
# - Why
# - What prevents recurrence
```

---

## Environment Promotion

```
.envs/.env.dev      → Local development
Railway Variables   → Staging + Production (set via CLI/dashboard)
Vercel Variables    → Frontend (set via dashboard)

Never commit secrets. Never put secrets in Dockerfile.
```
