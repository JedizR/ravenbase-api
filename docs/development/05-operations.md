# Development — 05. Operations & Production Checklist

> **Cross-references:** `architecture/06-observability.md` | `development/04-deployment.md`

---

## Monitoring Stack

| Tool | Purpose | Cost | Setup |
|---|---|---|---|
| Sentry | Exception tracking + performance | Free tier | `pip install sentry-sdk[fastapi]` |
| Grafana Cloud | Metrics, logs, APM | Free tier (10K series) | Prometheus exporter |
| Better Uptime | Uptime monitoring + alerts | Free (50 monitors) | Add `/health` endpoint URL |
| Railway Logs | Application logs | Included | Auto-collected |

---

## Health Endpoint

```python
# src/api/routes/health.py
# Always returns 200 or 503 based on REAL dependency checks

@router.get("/health")
async def health_check() -> dict:
    checks = {}

    # PostgreSQL
    try:
        await db.execute("SELECT 1")
        checks["postgresql"] = "ok"
    except Exception as e:
        checks["postgresql"] = f"ERROR: {e}"

    # Redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"ERROR: {e}"

    # Qdrant
    try:
        await qdrant.get_collection_info()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"ERROR: {e}"

    # Neo4j
    try:
        await neo4j.verify_connectivity()
        checks["neo4j"] = "ok"
    except Exception as e:
        checks["neo4j"] = f"ERROR: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if all_ok else "degraded", "checks": checks, "version": "1.0.0"},
    )
```

---

## Incident Response

### Detection (< 5 min)
- Better Uptime pings `/health` every 60 seconds
- Alert: email if 503 for > 2 consecutive checks

### Assess (5 min)
```bash
# Check service status
railway logs --service ravenbase-api | tail -50

# Check error rate in Sentry dashboard
# Check dead letter queue depth
redis-cli LLEN arq:dead-jobs
```

### Rollback (< 10 min)
See `development/04-deployment.md` — Rollback Procedure.

### Fix + Post-mortem (30 min)
```
docs/incidents/YYYY-MM-DD.md:
- What broke
- Root cause
- Fix applied
- Prevention measure
```

---

## Production Operations Checklist

Review before first customer onboarding:

### Architecture ✓
- [ ] Three-layer separation enforced: API / Service / Adapter
- [ ] No business logic in route handlers
- [ ] All adapters have `cleanup()` method
- [ ] No direct DB calls in services (always via adapters)
- [ ] All heavy imports are lazy (`# noqa: PLC0415`)
- [ ] Tenant isolation: every DB/Qdrant/Neo4j query filters by tenant_id

### Configuration ✓
- [ ] All secrets in Railway environment variables (not in code or .env committed)
- [ ] `pydantic-settings` with `Field(...)` for required secrets
- [ ] `APP_ENV=production` set in Railway
- [ ] `ENABLE_PII_MASKING=true` in production
- [ ] `CONFLICT_SIMILARITY_THRESHOLD=0.87` configured

### Reliability ✓
- [ ] ARQ SIGTERM handler working (tested with `kill -TERM <pid>`)
- [ ] Job retry configured (max_tries=3) for ingestion, graph, conflict tasks
- [ ] Dead Letter Queue monitored (Grafana alert if depth > 0)
- [ ] SHA-256 deduplication prevents re-processing same file
- [ ] Alembic migration runs as pre-deploy step

### Observability ✓
- [ ] Sentry DSN configured, `send_default_pii=False`
- [ ] structlog configured with JSON output in production
- [ ] All log lines include `tenant_id` and `job_id` where applicable
- [ ] `/health` endpoint returns real dependency checks (not just 200 always)
- [ ] Better Uptime monitoring active on `/health`
- [ ] Grafana dashboard: request rate, p95 latency, queue depth, error rate

### Security ✓
- [ ] Clerk JWT validated on every protected endpoint
- [ ] CORS `allow_origins` restricted to `ravenbase.app` only
- [ ] Rate limiting active (per-user Redis sliding window)
- [ ] MIME + magic bytes validation on file uploads
- [ ] PII masking enabled before all external LLM calls
- [ ] Qdrant filter enforced: every search includes tenant_id
- [ ] Neo4j WHERE clause enforced: every query filters by tenant_id
- [ ] PostgreSQL RLS enabled on all user data tables

### Database ✓
- [ ] Supabase PITR (point-in-time recovery) enabled
- [ ] Alembic migration history matches production schema
- [ ] Connection pooling sufficient (default SQLModel pool)
- [ ] All indexes created (idx_sources_user_id, idx_conflicts_user_id_status, etc.)

### Async Correctness ✓
- [ ] `asyncio.get_running_loop()` used (not deprecated `get_event_loop()`)
- [ ] All blocking I/O in async context uses `run_in_executor`
- [ ] All operations > 2s go through ARQ queue

### Frontend ✓
- [ ] OpenAPI client auto-generated and committed
- [ ] Clerk token attached to all API requests (`apiFetch`)
- [ ] All async job states handled: idle, uploading, processing, success, error
- [ ] Mobile responsive (tested at 375px)
- [ ] Lighthouse CI score > 90 on mobile (performance, accessibility, SEO)
- [ ] Dark mode works correctly on dashboard routes
- [ ] Light mode works correctly on marketing routes
- [ ] `npm run build` passes with 0 TypeScript errors

### Test Quality ✓
- [ ] `make ci-local` passes from clean checkout
- [ ] Coverage ≥ 70% (combined unit + integration)
- [ ] Tenant isolation test passes
- [ ] GDPR deletion cascade test passes
- [ ] Critical path E2E: register → upload → search → generate meta-doc

### Infrastructure & Env Vars ✓
- [ ] **Multi-database restore procedure verified:** Supabase PITR, Qdrant Cloud snapshot, and Neo4j AuraDB backup restored to the **same point in time**. Restore order: (1) PostgreSQL first (authoritative source of truth), (2) Qdrant (`make reindex-missing` to re-index any sources present in Postgres but missing from snapshot), (3) Neo4j (`make regraph-missing` to re-run graph extraction for sources with `status=completed` but missing Neo4j nodes)
- [ ] `MAX_DAILY_LLM_SPEND_USD` set in Railway production environment (start with 200.0 USD/day)
- [ ] `GEMINI_API_KEY` set in Railway production environment
- [ ] `RESEND_WEBHOOK_SECRET` set in Railway production environment
- [ ] `ADMIN_USER_IDS` set in Railway production environment (your Clerk user ID)
- [ ] Grafana/Better Uptime alert on `llm_circuit_breaker.approaching_cap` log event (warning)
- [ ] Grafana/Better Uptime alert on `llm_circuit_breaker.TRIPPED` log event (critical — immediate action required)

### Cost Controls ✓
- [ ] Credit system: per-operation deductions active
- [ ] Pre-generation credit check: insufficient credits → 402 before LLM call
- [ ] Free tier ingestion cap: 10 uploads/hour enforced
- [ ] Docling image generation disabled (saves CPU on every PDF)
- [ ] OpenAI embeddings batched (not one-by-one)

### Legal ✓
- [ ] Privacy Policy live and linked from footer
- [ ] Terms of Service live and linked from footer
- [ ] GDPR deletion endpoint working (`DELETE /v1/account`)
- [ ] Cookie consent banner (if using analytics)
- [ ] DPA signed with Supabase, OpenAI, Anthropic

---

## ARQ Queue Monitoring

```bash
# Check queue depths
redis-cli LLEN arq:queue:default
redis-cli LLEN arq:dead-jobs

# List running jobs
redis-cli SMEMBERS arq:in-progress

# Check worker health
redis-cli GET arq:health-check

# Clear dead letter queue (after investigating)
redis-cli DEL arq:dead-jobs
```

---

## Database Backup Verification

```bash
# Verify Supabase PITR is enabled
# → Supabase Dashboard → Settings → Database → Point-in-Time Recovery

# Test restore (to a staging environment, never production):
# supabase db restore --project-ref <staging-ref> --recovery-timestamp <timestamp>

# Qdrant snapshot (weekly):
curl -X POST https://<qdrant-url>/collections/ravenbase_chunks/snapshots
```
