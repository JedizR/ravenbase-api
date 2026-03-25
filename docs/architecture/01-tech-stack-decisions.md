# Architecture — 01. Tech Stack Decisions (ADRs)

> **Cross-references:** `architecture/00-system-overview.md` | `development/01-dev-environment.md`
>
> **Format:** Each decision = ADR (Architecture Decision Record) with context, decision, rationale, and rejected alternatives.

---

## ADR-001: Job Queue — ARQ (Python) over BullMQ (Node.js)

**Decision:** Use **ARQ** (Async Redis Queue, Python) for all background jobs.

**Context:** The backend is Python/FastAPI. Background jobs involve Docling (Python), OpenAI SDK (Python), Neo4j driver (Python). A Node.js queue would require a separate Node process to orchestrate Python workers, creating an unnecessary polyglot boundary.

**Rationale:**
- ARQ is async-native (Python asyncio) — no thread pool overhead
- Same language as FastAPI and workers — single codebase, shared Pydantic models
- Backed by Redis (already in stack) — no additional infrastructure
- Simple API: `await arq.enqueue_job("task_name", kwarg=value)`
- Graceful SIGTERM shutdown built-in (critical for Railway ephemeral deploys)

**Rejected alternatives:**
- BullMQ: Node.js only — would require Node process to manage Python workers
- Celery: heavyweight, requires separate broker config, complex for solo dev
- RabbitMQ: additional infrastructure, overkill for MVP scale

---

## ADR-002: Vector Store — Qdrant over OpenSearch

**Decision:** Use **Qdrant** as the primary vector store.

**Context:** The original PRD specified OpenSearch (from OpenRAG blueprint). After analysis, Qdrant is strictly better for this use case at MVP scale.

**Rationale:**
- Qdrant is purpose-built for vector search — no BM25 index overhead on simple semantic queries
- Docker image is 200MB vs OpenSearch's 1GB+ multi-container setup
- Qdrant Cloud free tier: 1GB storage, sufficient for MVP (est. 50K chunks)
- Python SDK is excellent; filtering by metadata (tenant_id, profile_id) is first-class
- Hybrid search (dense + sparse BM25) available via `sparse_vectors` — covers the keyword search use case
- OpenSearch migration path is documented if scale demands it post-MVP

**Rejected alternatives:**
- OpenSearch: operationally complex (Java, 2+ containers, high RAM), overkill for MVP
- Pinecone: vendor lock-in, no self-host option, expensive at scale
- pgvector: PostgreSQL extension; insufficient for high-throughput vector search

---

## ADR-003: Frontend → Backend Contract — OpenAPI Generated Client over tRPC

**Decision:** Use **auto-generated TypeScript client from FastAPI's OpenAPI spec** for frontend→backend communication.

**Context:** tRPC requires a TypeScript server. Our backend is Python/FastAPI, which auto-generates `/openapi.json`. Using `@hey-api/openapi-ts` generates a fully typed TypeScript client from this spec.

**Rationale:**
- Zero manual type duplication — change backend response shape, frontend gets a TypeScript error
- AI agents can generate correct API calls by reading the generated client
- FastAPI OpenAPI spec is always up-to-date (generated from Pydantic models)
- `npm run generate-client` takes 5 seconds; run whenever backend schema changes

**Rejected alternatives:**
- tRPC: requires TypeScript backend — incompatible with Python/FastAPI
- Manual TypeScript interfaces: duplicates types, guaranteed to drift

---

## ADR-004: Authentication — Clerk over Supabase Auth

**Decision:** Use **Clerk** for authentication (frontend + backend).

**Context:** Both Clerk and Supabase Auth are viable. Supabase Auth is bundled with our Supabase subscription.

**Rationale:**
- Clerk's JWT is verifiable in FastAPI using the `clerk-backend` SDK — single provider for both layers
- Supabase Auth JWTs require additional configuration to validate in non-Supabase backends
- Clerk's UI components (SignIn, SignUp, UserButton) are production-grade and reduce frontend code
- Clerk free tier covers up to 10K MAU — sufficient for MVP and significant growth
- Clerk provides organizations/teams feature for future multi-seat plans

**Rejected alternatives:**
- Supabase Auth: JWT validation in external FastAPI backend requires custom implementation; Clerk is simpler
- Auth0: more expensive; overkill for solo dev

---

## ADR-005: ORM — SQLModel over SQLAlchemy + Pydantic separately

**Decision:** Use **SQLModel** (combines SQLAlchemy + Pydantic) for all database models.

**Rationale:**
- Single class definition serves as both the ORM model and the Pydantic schema
- FastAPI integration is first-class (SQLModel was designed by the FastAPI author)
- Reduces boilerplate significantly — critical for solo developer productivity
- Still uses SQLAlchemy under the hood — all advanced features available if needed

---

## ADR-006: Database Migrations — Alembic (mandatory)

**Decision:** Use **Alembic** for all database schema changes. `SQLModel.metadata.create_all()` is forbidden in production.

**Rationale:**
- Migration history enables precise rollback — critical for production safety
- `alembic revision --autogenerate` detects model changes and generates migration SQL
- `alembic downgrade -1` is the standard rollback procedure
- Per BMAD blueprint: "never `create_all()` in production"

---

## ADR-007: Python Package Manager — uv over pip/poetry

**Decision:** Use **uv** for all Python package management.

**Rationale:**
- 10-100x faster than pip for installs
- `uv.lock` provides reproducible installs (commit to git — never .gitignore)
- `uv sync --dev` installs all dependencies including dev tools
- Compatible with `pyproject.toml` standard

---

## ADR-008: Deployment — Railway (backend) + Vercel (frontend)

**Decision:** Railway for backend API + Worker; Vercel for Next.js frontend.

**Rationale for Railway:**
- 1-click deploy from GitHub
- Managed Redis included
- Supports multiple dynos (API + Worker as separate processes)
- Predictable pricing (~$20/mo for hobby tier)
- Supports custom Docker images for Docling workers

**Rationale for Vercel:**
- Zero-config Next.js deployment
- Edge functions for API routes (landing page performance)
- Automatic preview deployments on PRs
- Free tier sufficient for MVP

---

## ADR-009: Graph Database — Neo4j AuraDB Free

**Decision:** Use **Neo4j AuraDB Free tier** for the knowledge graph.

**Rationale:**
- 50K node limit is sufficient for MVP (est. 10K nodes per active user × 5 beta users)
- Managed cloud service — zero operational overhead
- Cypher query language is well-documented and AI-agent-friendly
- Upgrade path to AuraDB Pro is seamless ($65/mo for 1M nodes)
- Neo4j Python driver is mature and well-typed

---

## ADR-010: Structured Logging — structlog over Python logging

**Decision:** Use **structlog** for all application logging. `print()` is forbidden.

**Rationale:**
- Structured JSON output — compatible with Grafana Loki and Railway log aggregation
- Context binding: `logger.bind(tenant_id=..., job_id=...)` propagates through all log lines
- Consistent format makes log parsing trivial
- Per BMAD blueprint: "structured JSON logs, include tenant_id, job_id"

---

## Complete Tech Stack Reference

| Layer | Technology | Version |
|---|---|---|
| **Frontend framework** | Next.js (App Router) | 15.x |
| **Frontend styling** | Tailwind CSS | 4.x |
| **Frontend components** | shadcn/ui (New York style) | latest |
| **Frontend state** | TanStack Query (React Query) | v5 |
| **Frontend auth** | Clerk Next.js SDK | latest |
| **Frontend fonts** | DM Sans + Playfair Display + JetBrains Mono | Google Fonts |
| **Frontend deploy** | Vercel | — |
| **Backend framework** | FastAPI | 0.115+ |
| **Backend language** | Python | 3.12 |
| **Backend package mgr** | uv | latest |
| **Backend ORM** | SQLModel | latest |
| **Database** | PostgreSQL 16 | Supabase managed |
| **Migrations** | Alembic | latest |
| **Job queue** | ARQ | latest |
| **Cache/pub-sub** | Redis 7 | Railway managed |
| **Vector store** | Qdrant | Cloud free / Docker |
| **Graph database** | Neo4j AuraDB | Free tier |
| **File storage** | Supabase Storage | S3-compatible |
| **Document parser** | Docling (IBM) | latest |
| **Embeddings** | OpenAI text-embedding-3-small | 1536-dim |
| **Fast LLM** | Anthropic Claude Haiku | latest |
| **Reasoning LLM** | Anthropic Claude Sonnet | latest |
| **PII detection** | Microsoft Presidio | latest |
| **Auth provider** | Clerk | latest |
| **Error tracking** | Sentry | latest |
| **Logging** | structlog | latest |
| **Backend deploy** | Railway | — |
| **Backend linting** | Ruff | 0.15+ |
| **Backend type check** | Pyright | 1.1+ |
| **Frontend type check** | TypeScript strict | 5.x |
| **Testing (backend)** | pytest + pytest-asyncio + pytest-xdist | latest |
| **Testing (frontend)** | Vitest + Playwright | latest |
| **CI/CD** | GitHub Actions | — |
| **Monitoring** | Grafana Cloud (free) + Sentry | — |
| **Payments** | Stripe | — |
| **Email** | Resend | — |

---

## ADR-011: LLM Multi-Provider Strategy — LiteLLM SDK + Task-Tiered Routing

**Decision:** Use the `litellm` Python SDK as a unified adapter layer over multiple LLM
providers, with task-based routing to optimize cost and availability.

**Context:**
The original architecture hard-coded Anthropic for all LLM tasks, creating two risks:
(1) Anthropic outages stall the entire ingestion pipeline;
(2) Background tasks use Claude Haiku ($1/$5 per 1M tokens) when Google Gemini 2.5 Flash
delivers identical structured JSON output for $0.30/$2.50 — 67–70% cheaper on the
most-executed tasks in the system.

**Decision:**
Implement a `LLMRouter` service using LiteLLM as the Python SDK for unified calling
and automatic failover. No separate proxy server — litellm used as a library only.

**Task-to-Model Routing Table:**

| Task type | Primary | Fallback | Rationale |
|---|---|---|---|
| Entity extraction | `gemini/gemini-2.5-flash` | `anthropic/claude-haiku-4-5-20251001` | 67% cheaper, identical JSON quality |
| Conflict classification | `gemini/gemini-2.5-flash` | `anthropic/claude-haiku-4-5-20251001` | Same |
| Cypher generation | `gemini/gemini-2.5-flash` | `anthropic/claude-haiku-4-5-20251001` | Same |
| Meta-Doc generation (Haiku tier) | `anthropic/claude-haiku-4-5-20251001` | `gemini/gemini-2.5-flash` | User-visible quality — keep Claude |
| Meta-Doc generation (Sonnet tier) | `anthropic/claude-sonnet-4-6` | `anthropic/claude-haiku-4-5-20251001` | Best quality — keep Claude |
| Chat (Haiku tier) | `anthropic/claude-haiku-4-5-20251001` | `gemini/gemini-2.5-flash` | Citations quality |
| Chat (Sonnet tier) | `anthropic/claude-sonnet-4-6` | `anthropic/claude-haiku-4-5-20251001` | Same |
| Embeddings | `openai/text-embedding-3-small` | N/A | No comparable alternative |

**Fallback triggers (handled by litellm automatically):**
- HTTP 5xx from primary provider
- HTTP 429 (rate limit exhausted after 2 retries)
- Timeout exceeding task SLO

**LLMRouter implementation (`src/adapters/llm_router.py`):**

```python
# src/adapters/llm_router.py
# REPLACES direct Anthropic calls for pipeline tasks.
# anthropic_adapter.py RETAINED for user-facing streaming SSE.
# openai_adapter.py RETAINED for embeddings only.

import os
import litellm  # noqa: PLC0415 — lazy import at module usage
from structlog import get_logger

log = get_logger()

TASK_MODELS: dict[str, tuple[str, str]] = {
    "entity_extraction":       ("gemini/gemini-2.5-flash", "anthropic/claude-haiku-4-5-20251001"),
    "conflict_classification": ("gemini/gemini-2.5-flash", "anthropic/claude-haiku-4-5-20251001"),
    "cypher_generation":       ("gemini/gemini-2.5-flash", "anthropic/claude-haiku-4-5-20251001"),
    "metadoc_haiku":           ("anthropic/claude-haiku-4-5-20251001", "gemini/gemini-2.5-flash"),
    "metadoc_sonnet":          ("anthropic/claude-sonnet-4-6", "anthropic/claude-haiku-4-5-20251001"),
    "chat_haiku":              ("anthropic/claude-haiku-4-5-20251001", "gemini/gemini-2.5-flash"),
    "chat_sonnet":             ("anthropic/claude-sonnet-4-6", "anthropic/claude-haiku-4-5-20251001"),
}

class LLMRouter:
    async def complete(
        self,
        task: str,
        messages: list[dict],
        response_format: dict | None = None,
        max_tokens: int = 2048,
    ) -> str:
        primary, fallback = TASK_MODELS[task]
        response = await litellm.acompletion(
            model=primary,
            messages=messages,
            max_tokens=max_tokens,
            response_format=response_format,
            fallbacks=[fallback],
            num_retries=2,
            request_timeout=60,
            metadata={"task": task},
        )
        log.info("llm_router.complete", task=task, model=primary,
                 input_tokens=response.usage.prompt_tokens,
                 output_tokens=response.usage.completion_tokens)
        return response.choices[0].message.content

    async def complete_streaming(self, task: str, messages: list[dict], max_tokens: int = 4096):
        primary, fallback = TASK_MODELS[task]
        response = await litellm.acompletion(
            model=primary, messages=messages, max_tokens=max_tokens,
            stream=True, fallbacks=[fallback], num_retries=1, request_timeout=300,
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

**New packages:**
- `litellm>=1.30.0` (lazy import in `llm_router.py`)
- `google-generativeai>=0.8.0` (Gemini backend for litellm)

**Consequences:**
- Background task LLM cost drops ~67%
- Platform resilient to single-provider outage
- New env var: `GEMINI_API_KEY` (optional — falls back to Claude Haiku if absent)
