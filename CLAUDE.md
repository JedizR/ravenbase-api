# Ravenbase — Agent Master Instructions (CLAUDE.md)

> **CRITICAL:** Read this file completely before implementing any story.
> This is your architecture constitution. Every rule here exists to prevent rewrites.

---

## Project Overview

Ravenbase is a **Human-AI Long-Term Context Memory System** — a SaaS platform that permanently captures, structures, and synthesizes a user's knowledge using a hybrid vector + knowledge graph architecture.

**Two repos:**
- `ravenbase-api/` — Python FastAPI backend (this is the backend repo)
- `ravenbase-web/` — Next.js 15 frontend (separate repo)

**Docs live in:** `ravenbase-api/docs/` (monorepo-style docs, consumed by both agents)

---

## ABSOLUTE ARCHITECTURE RULES (Never Violate)

```
RULE 1: Three layers. Always.
  API layer (routes) → Service layer (business logic) → Adapter layer (external systems)
  Nothing bleeds between layers.
  ❌ Database query inside a route handler
  ❌ Business logic inside an adapter
  ❌ HTTP calls inside a service

RULE 2: All tenant data is ALWAYS filtered by tenant_id.
  Every Qdrant query: must include tenant_id filter
  Every Neo4j query: must use tenant_id WHERE clause
  Every PostgreSQL query: scoped via Supabase RLS or explicit WHERE user_id = ?
  ❌ NEVER return data without tenant_id filter — this is a security breach

RULE 3: Every operation >2 seconds uses ARQ queue.
  ❌ NEVER run Docling/embedding/LLM calls synchronously in an API route
  ✅ Route returns job_id immediately; worker does the work
  ✅ Client polls /v1/jobs/{job_id} or uses SSE stream

RULE 4: Write models/schemas FIRST, tests SECOND, implementation THIRD.
  This prevents misunderstandings and makes AI output reviewable.

RULE 5: All secrets in environment variables. Nothing in code.
  Use pydantic-settings with @lru_cache for settings.
  Required secrets use Field(...) — app fails loudly if missing.

RULE 6: Heavy imports are lazy.
  Any ML/heavy library import must be inside the function body.
  ❌ import torch at module level
  ✅ def load_model(): import torch  # noqa: PLC0415

RULE 7: No print() statements. Ever.
  Use structlog for all logging. Include tenant_id and job_id in every log.

RULE 8: Tests must pass before reporting completion.
  Run: make quality && make test
  If tests fail, fix before reporting.

RULE 9: Sanitize all LLM output before storing or rendering.
  Run bleach.clean() on Meta-Document content before DB write.
  Never use dangerouslySetInnerHTML for LLM-generated content in the frontend.
  Always validate LLM JSON responses against Pydantic schema before use.

RULE 10 (Backend security): All user-controlled content in LLM prompts must be
  wrapped in XML boundary tags.
  ❌ f"Extract from: {user_text}\nNow output JSON"
  ✅ f"Output JSON.\n<user_document>{user_text}</user_document>"

RULE 11 (Cypher): tenant_id is ALWAYS a Neo4j query parameter, NEVER string-interpolated.
  ❌ f"MATCH (m) WHERE m.tenant_id = '{tenant_id}'"
  ✅ session.run(query, tenant_id=tenant_id)
```

---

## Repository Structure (Backend)

```
ravenbase-api/
├── CLAUDE.md                    ← This file
├── CLAUDE_BACKEND.md            ← Backend-specific patterns
├── pyproject.toml               ← uv package manager
├── uv.lock                      ← COMMITTED to git (never .gitignore)
├── ruff.toml
├── pyrightconfig.json
├── .pre-commit-config.yaml
├── Makefile
├── Dockerfile.api
├── Dockerfile.worker
├── docker-compose.yml           ← Base (postgres, redis)
├── docker-compose.override.yml  ← Dev (live reload, dev env)
├── docker-compose.prod.yml      ← Production
├── .envs/
│   ├── .env.dev                 ← Never commit
│   └── .env.example             ← Template — commit this
├── alembic/
│   ├── env.py
│   └── versions/                ← Migration files
├── src/
│   ├── api/
│   │   ├── main.py              ← FastAPI app + lifespan
│   │   ├── dependencies/
│   │   │   ├── auth.py          ← require_user (Clerk JWT validation)
│   │   │   └── db.py            ← get_db session dependency
│   │   └── routes/
│   │       ├── ingest.py
│   │       ├── search.py
│   │       ├── conflict.py
│   │       ├── graph.py
│   │       ├── metadoc.py
│   │       └── health.py
│   ├── services/
│   │   ├── base.py              ← BaseService with cleanup()
│   │   ├── ingestion_service.py
│   │   ├── rag_service.py
│   │   ├── conflict_service.py
│   │   ├── graph_service.py
│   │   └── metadoc_service.py
│   ├── adapters/
│   │   ├── base.py              ← BaseAdapter
│   │   ├── docling_adapter.py   ← Document parsing
│   │   ├── openai_adapter.py    ← Embeddings + LLM calls
│   │   ├── anthropic_adapter.py ← Claude API calls
│   │   ├── qdrant_adapter.py    ← Vector store
│   │   └── neo4j_adapter.py     ← Graph database
│   ├── workers/
│   │   ├── main.py              ← ARQ worker entrypoint
│   │   ├── ingestion_tasks.py   ← parse_document, chunk_text, embed
│   │   ├── graph_tasks.py       ← extract_entities, write_nodes
│   │   ├── conflict_tasks.py    ← scan_conflicts, classify
│   │   └── deletion_tasks.py    ← cascade_delete
│   ├── models/
│   │   ├── user.py
│   │   ├── source.py
│   │   ├── profile.py
│   │   └── meta_document.py
│   ├── schemas/
│   │   ├── ingest.py            ← Request/response Pydantic models
│   │   ├── search.py
│   │   ├── conflict.py
│   │   └── common.py            ← Shared (PaginatedResponse, etc.)
│   └── core/
│       ├── config.py            ← pydantic-settings
│       ├── logging.py           ← structlog setup
│       └── errors.py            ← Error codes + HTTPException helpers
└── tests/
    ├── conftest.py
    ├── unit/
    │   └── services/
    └── integration/
        └── api/
```

---

## Model Selection Policy

Ravenbase uses **task-tiered LLM routing** via `src/adapters/llm_router.py` (LiteLLM SDK).
Two categories: background pipeline (cost-optimized) and user-facing generation (quality-optimized).
**Never call Anthropic or Gemini SDKs directly in the service layer — always use `LLMRouter`.**

### Background pipeline tasks — cost-optimized, NOT user-configurable
Primary: Gemini 2.5 Flash | Fallback: Claude Haiku (automatic, via litellm)

| Task | Primary | Fallback |
|---|---|---|
| Entity extraction | `gemini/gemini-2.5-flash` | `anthropic/claude-haiku-4-5-20251001` |
| Conflict classification | `gemini/gemini-2.5-flash` | `anthropic/claude-haiku-4-5-20251001` |
| Cypher generation | `gemini/gemini-2.5-flash` | `anthropic/claude-haiku-4-5-20251001` |

### User-facing generation — user-configurable via `preferred_model` setting
Default: Claude Haiku | Pro option: Claude Sonnet | Fallback: Gemini Flash on provider outage

| Task | Default | Pro option | Fallback |
|---|---|---|---|
| Meta-Doc synthesis | `anthropic/claude-haiku-4-5-20251001` | `anthropic/claude-sonnet-4-6` | `gemini/gemini-2.5-flash` |
| Memory chat | `anthropic/claude-haiku-4-5-20251001` | `anthropic/claude-sonnet-4-6` | `gemini/gemini-2.5-flash` |

> **Model switching (Haiku→Sonnet) is a Pro subscription feature.** Free tier users
> always use Haiku for generation tasks regardless of preferences. This is enforced
> in the credit check middleware, not just the UI.

### Embeddings
- `openai/text-embedding-3-small` — no routing, no fallback, always OpenAI

### Usage in code

```python
# ✅ Correct — use LLMRouter in service layer
from src.adapters.llm_router import LLMRouter
result = await LLMRouter().complete("entity_extraction", messages=[...])

# ❌ Wrong — never in service layer
from anthropic import AsyncAnthropic
```

---

## Service Layer Pattern

Every service extends BaseService:

```python
# src/services/base.py
from abc import ABC

class BaseService(ABC):
    """All services extend this. cleanup() releases resources."""

    def cleanup(self) -> None:
        """Override to release adapters, close connections."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        self.cleanup()
```

Service implementation pattern:

```python
# src/services/ingestion_service.py
from structlog import get_logger
from src.services.base import BaseService
from src.adapters.docling_adapter import DoclingAdapter
from src.schemas.ingest import IngestResult

logger = get_logger()

class IngestionService(BaseService):
    def __init__(self, adapter: DoclingAdapter | None = None) -> None:
        self._adapter = adapter  # injected in tests, lazy-created in prod

    def _get_adapter(self) -> DoclingAdapter:
        if self._adapter is None:
            self._adapter = DoclingAdapter()
        return self._adapter

    async def process_document(
        self,
        content: bytes,
        filename: str,
        tenant_id: str,
        source_id: str,
    ) -> IngestResult:
        log = logger.bind(tenant_id=tenant_id, source_id=source_id, filename=filename)
        log.info("ingestion.started")
        result = await self._get_adapter().parse(content, filename)
        log.info("ingestion.completed", chunk_count=result.chunk_count)
        return result

    def cleanup(self) -> None:
        if self._adapter:
            self._adapter.cleanup()
```

---

## API Route Pattern

Routes are thin. No business logic.

```python
# src/api/routes/ingest.py
from fastapi import APIRouter, Depends, UploadFile
from src.api.dependencies.auth import require_user
from src.services.ingestion_service import IngestionService
from src.schemas.ingest import UploadResponse

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile,
    user: dict = Depends(require_user),
) -> UploadResponse:
    """Enqueue file for background processing. Returns job_id immediately."""
    content = await file.read()
    job_id = await enqueue_ingestion(
        content=content,
        filename=file.filename,
        tenant_id=user["user_id"],
    )
    return UploadResponse(job_id=job_id, status="queued")
```

---

## Authentication (Clerk)

```python
# src/api/dependencies/auth.py
import httpx
import jwt
from fastapi import Header, HTTPException
from src.core.config import settings

# Fetch Clerk's JWKS once at startup (cached in-process)
_clerk_jwks_client: jwt.PyJWKClient | None = None

def _get_jwks_client() -> jwt.PyJWKClient:
    global _clerk_jwks_client
    if _clerk_jwks_client is None:
        jwks_url = f"https://{settings.CLERK_FRONTEND_API}/.well-known/jwks.json"
        _clerk_jwks_client = jwt.PyJWKClient(jwks_url)
    return _clerk_jwks_client

async def require_user(authorization: str | None = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "MISSING_AUTH", "message": "Authorization header required"},
        )
    token = authorization.removeprefix("Bearer ")
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True},
        )
        return {"user_id": payload["sub"], "email": payload.get("email", "")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=403,
            detail={"code": "TOKEN_EXPIRED", "message": "Token has expired"},
        )
    except Exception:
        raise HTTPException(
            status_code=403,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        )
```

**Required env var:** `CLERK_FRONTEND_API` — your Clerk frontend API domain, looks like
`your-app.clerk.accounts.dev`. Found in Clerk Dashboard → API Keys.
Add to `.envs/.env.example` and `.envs/.env.dev`.

---

## Error Handling Pattern

```python
# src/core/errors.py
from fastapi import HTTPException

class ErrorCode:
    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"
    INGESTION_FAILED = "INGESTION_FAILED"
    CONFLICT_NOT_FOUND = "CONFLICT_NOT_FOUND"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"

def raise_404(code: str, detail: str) -> None:
    raise HTTPException(status_code=404, detail={"code": code, "message": detail})

def raise_422(code: str, detail: str) -> None:
    raise HTTPException(status_code=422, detail={"code": code, "message": detail})

def raise_429(code: str, detail: str) -> None:
    raise HTTPException(status_code=429, detail={"code": code, "message": detail})
```

---

## Dependency Management Rules

**ALWAYS ask before adding a new package.**
Propose: the package name, why it's needed, and whether it's in `dependencies` or `dev`.

Approved packages (already in pyproject.toml — do NOT add without asking):

**API server:**
- `fastapi`, `uvicorn[standard]`

**Database + migrations:**
- `sqlmodel` — ORM + Pydantic models combined
- `alembic` — migrations (never use create_all() in production)

**Job queue:**
- `arq` — Async Redis Queue (Python, NOT BullMQ which is Node.js)
- `redis` — Redis client

**Storage:**
- `qdrant-client` — vector store (NOT OpenSearch)
- `neo4j` — graph database driver
- `supabase` — Supabase Python client for Storage file operations

**AI:**
- `openai` — embeddings only (`text-embedding-3-small` in `openai_adapter.py`)
- `anthropic` — Claude Haiku/Sonnet for user-facing generation + streaming SSE (`anthropic_adapter.py` retained)
- `litellm>=1.30.0` — unified LLM SDK; handles Gemini + Anthropic routing + fallback (lazy import in `llm_router.py`)
- `google-generativeai>=0.8.0` — Gemini provider backend for litellm (background tasks)
- `presidio-analyzer`, `presidio-anonymizer` — PII detection

**Auth + webhooks:**
- `PyJWT>=2.9.0` — Clerk JWT validation via JWKS endpoint (replaces clerk-backend-api)
- `cryptography>=43.0.0` — Required by PyJWT for RS256 algorithm support
- `svix` — Clerk webhook signature validation (used in /webhooks/clerk route)
- `stripe>=10.0.0` — Stripe Python SDK for payment webhooks and checkout (STORY-022 only)

**File handling:**
- `python-magic` — MIME type detection from file magic bytes (file validation in upload)
- `aiofiles` — async file I/O for Docling temp file handling

**Networking + streaming:**
- `httpx` — async HTTP client (test suite + inter-service)
- `sse-starlette` — Server-Sent Events (job progress streaming)

**Observability:**
- `structlog` — structured logging (no print() ever)
- `sentry-sdk[fastapi]` — error tracking

**Config:**
- `pydantic-settings` — settings management with @lru_cache

**Security:**
- `bleach>=6.1.0` — HTML sanitization for LLM output before storage (Meta-Doc service)

**Email:**
- `resend>=2.5.0` — transactional email via Resend API (STORY-032 only; lazy import inside service methods)

**Dev tools (dependency-groups.dev):**
- `ruff`, `pyright`, `pre-commit`
- `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `pytest-xdist`
- `httpx` — also used in tests
- `aiosqlite` — async SQLite driver for in-memory tests

---

## Common Mistakes to Avoid

```
❌ Don't use BullMQ — that's Node.js. Use ARQ (Python).
❌ Don't use tRPC — that's TypeScript-to-TypeScript. Frontend uses generated OpenAPI client.
❌ Don't create ad-hoc database sessions — always use Depends(get_db)
❌ Don't use SQLModel.metadata.create_all() in production — use Alembic
❌ Don't hardcode tenant_id — always get from require_user dependency
❌ Don't run heavy work in route handlers — enqueue to ARQ
❌ Don't catch bare Exception — catch specific exceptions and log with structlog
❌ Don't use asyncio.get_event_loop() — use asyncio.get_running_loop()
❌ Don't set CORS allow_origins=["*"] in production
❌ Don't call create_pool() inside a route handler
   ✅ The ARQ pool is initialized once in lifespan() → stored in app.state.arq_pool
   ✅ Access it in routes via: request.app.state.arq_pool.enqueue_job(...)
```

---

## Optional: Context7 MCP for Up-to-Date Library Docs

Claude Code can hallucinate outdated API patterns for libraries that change frequently
(FastAPI lifespan syntax, SQLModel async patterns, ARQ WorkerSettings, Qdrant filter API).

To give Claude Code access to live documentation, install the Context7 MCP:

```bash
# In your Claude Code settings or .mcp.json:
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

Usage in Claude Code: prefix your question with `use context7` to fetch live docs:
> "use context7 — how do I configure ARQ WorkerSettings with a custom health check?"
> "use context7 — what is the current SQLModel async session pattern?"

This is optional but recommended, especially for STORY-001 scaffolding and any story
that uses a library you haven't worked with recently.

---

## Before Every Implementation: Agent Checklist

```
□ Have I read the story file completely?
□ Have I read the relevant architecture docs referenced in the story?
□ Did I write Pydantic models/schemas FIRST?
□ Did I write tests BEFORE implementing?
□ Are all DB queries tenant-scoped?
□ Is heavy work queued to ARQ?
□ Are all imports at module level (no lazy violations)?
□ Did I use structlog (not print)?
□ Did I run make quality && make test?
□ Are all acceptance criteria met?
□ Did I update docs/stories/epics.md → changed this story's 🔲 to ✅?
□ Did I set docs/.bmad/story-counter.txt to the next backend story ID in the sequence?
  Backend sequence: 001→002→003→004→005→006→007-BE→008-BE→009→010→012→013→015→016→018-BE→023→024→025→026→028-BE→029→[BACKEND GATE]→036-BE→037
  (skips frontend-only stories: 011, 014, 017, 019-022, 027, 030-035, 036-FE)
□ Did I update docs/.bmad/project-status.md with current sprint and next story?
□ Did I append an entry to docs/.bmad/journal.md? (all 6 fields filled, stats table updated)
□ Did I commit ALL FOUR files in one commit: epics.md + project-status.md + story-counter.txt + journal.md?
```
