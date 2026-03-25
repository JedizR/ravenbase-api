# Architecture — 06. Observability

> **Cross-references:** `development/05-operations.md` | `development/02-coding-standards.md`

---

## Logging (structlog)

```python
# src/core/logging.py
import structlog
import logging

def setup_logging(is_production: bool = False) -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_production:
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
```

### Log Format (Production — JSON)

```json
{
  "timestamp": "2026-03-18T14:30:00.000Z",
  "level": "info",
  "logger": "src.workers.ingestion_tasks",
  "event": "ingestion.completed",
  "tenant_id": "uuid",
  "source_id": "uuid",
  "job_id": "arq:job:uuid",
  "chunk_count": 42,
  "duration_ms": 8420
}
```

### Required Fields Per Log Line

| Context | Required Fields |
|---|---|
| API request | `tenant_id`, `request_id` (from middleware) |
| Background job | `tenant_id`, `source_id`, `job_id`, `job_type` |
| LLM call | `tenant_id`, `model`, `tokens_used`, `duration_ms` |
| Error | `tenant_id`, `error_type`, `stack_trace` (exc_info=True) |

---

## Request Tracing (Middleware)

```python
# src/api/main.py — add trace ID to every request
import uuid
from structlog.contextvars import clear_contextvars, bind_contextvars

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    clear_contextvars()
    bind_contextvars(request_id=request_id)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

---

## Metrics (Prometheus)

```python
# src/api/main.py — expose /metrics endpoint
from prometheus_client import Counter, Histogram, make_asgi_app
import time

REQUEST_COUNT = Counter(
    "ravenbase_requests_total",
    "Total requests",
    ["method", "endpoint", "status_code"]
)
REQUEST_LATENCY = Histogram(
    "ravenbase_request_duration_seconds",
    "Request latency",
    ["endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)
JOB_COUNT = Counter(
    "ravenbase_jobs_total",
    "Background jobs",
    ["job_type", "status"]
)
QUEUE_DEPTH = Gauge(
    "ravenbase_queue_depth",
    "ARQ queue depth",
    ["queue_name"]
)
DEAD_LETTER_DEPTH = Gauge(
    "ravenbase_dead_letter_depth",
    "ARQ dead letter queue depth"
)

# Mount at /metrics (restrict to internal IPs in NGINX)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

### Key Alerts (Grafana)

| Alert | Condition | Severity |
|---|---|---|
| High error rate | Error rate > 5% over 5min | Critical |
| Slow API | p95 latency > 2s over 5min | Warning |
| Dead letter queue | depth > 0 | Warning |
| Ingestion failures | failure rate > 10% over 30min | Warning |
| Low credits warning | User credits < 50 | Info (user notification) |

---

## Error Tracking (Sentry)

```python
# src/api/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[
        FastApiIntegration(transaction_style="endpoint"),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=0.1,   # 10% of requests traced
    profiles_sample_rate=0.1,
    send_default_pii=False,   # NEVER send PII to Sentry
    environment=settings.APP_ENV,
)
```

### Sentry Fingerprinting (Group Similar Errors)

```python
# In exception handlers:
with sentry_sdk.push_scope() as scope:
    scope.set_tag("tenant_id", tenant_id)
    scope.set_tag("job_type", job_type)
    scope.set_context("job", {"source_id": source_id, "filename": filename})
    sentry_sdk.capture_exception(e)
```

---

## Log Aggregation

Railway automatically collects stdout/stderr from all services. In production, use Railway's log drain to forward to Grafana Loki for querying:

```
Railway Log Drain → Grafana Loki → Grafana Dashboard
```

Key Loki queries:
```logql
# All errors for a specific tenant
{service="ravenbase-api"} |= "error" | json | tenant_id="uuid"

# Job failures
{service="ravenbase-worker"} |= "failed" | json | job_type="ingestion"

# Slow requests (> 1s)
{service="ravenbase-api"} | json | duration_ms > 1000
```
