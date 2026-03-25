# Development — 00. Project Structure

> **Cross-references:** `docs/CLAUDE.md` | `development/01-dev-environment.md`

---

## Backend Repo: `ravenbase-api`

```
ravenbase-api/
│
├── CLAUDE.md                          ← Agent master instructions (copy of docs/CLAUDE.md)
├── pyproject.toml                     ← uv dependencies + ruff/pyright config
├── uv.lock                            ← COMMITTED — never in .gitignore
├── ruff.toml
├── pyrightconfig.json
├── .pre-commit-config.yaml
├── Makefile
│
├── Dockerfile.api                     ← Multi-stage: builder + runtime (python:3.12-slim)
├── Dockerfile.worker                  ← Same base, runs ARQ
├── docker-compose.yml                 ← Base: postgres + redis services
├── docker-compose.override.yml        ← Dev: live-reload volumes + .env.dev
├── docker-compose.prod.yml            ← Prod: pinned image tags + .env.production
│
├── .envs/
│   ├── .env.example                   ← ALL variable names with comments (commit this)
│   ├── .env.dev                       ← Local development values (never commit)
│   └── .env.production                ← Production values (never commit; use Railway env)
│
├── alembic/
│   ├── alembic.ini
│   ├── env.py                         ← Auto-imports all SQLModel models for autogenerate
│   └── versions/
│       └── 001_initial_schema.py
│
├── scripts/
│   ├── seed_dev_data.py               ← Seeds 3 sample users + source files for local dev
│   ├── setup_qdrant.py                ← Creates collection if not exists
│   └── setup_neo4j.py                 ← Creates constraints + indexes
│
├── src/
│   ├── __init__.py
│   │
│   ├── api/                           ← API Layer: HTTP only, no business logic
│   │   ├── __init__.py
│   │   ├── main.py                    ← FastAPI app + lifespan + CORS + Sentry init
│   │   ├── dependencies/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                ← require_user (Clerk JWT validation)
│   │   │   └── db.py                  ← get_db (async SQLModel session)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── chat.py              ← STORY-026: /v1/chat/* endpoints (direct SSE, not ARQ)
│   │       ├── health.py              ← GET /health
│   │       ├── ingest.py              ← POST /v1/ingest/upload, /text, GET /stream
│   │       ├── sources.py             ← GET/DELETE /v1/sources
│   │       ├── search.py              ← POST /v1/search
│   │       ├── conflict.py            ← GET/POST /v1/conflicts
│   │       ├── graph.py               ← GET /v1/graph/nodes, /neighborhood
│   │       ├── metadoc.py             ← POST/GET /v1/metadoc
│   │       ├── profiles.py            ← CRUD /v1/profiles
│   │       ├── credits.py             ← GET /v1/credits/balance
│   │       ├── account.py             ← DELETE /v1/account (GDPR)
│   │       └── webhooks.py            ← POST /webhooks/clerk, /webhooks/stripe
│   │
│   ├── services/                      ← Service Layer: business logic only
│   │   ├── __init__.py
│   │   ├── base.py                    ← BaseService with cleanup()
│   │   ├── ingestion_service.py       ← parse, chunk, embed orchestration
│   │   ├── graph_service.py           ← entity extraction + Neo4j writes
│   │   ├── conflict_service.py        ← detection, classification, resolution
│   │   ├── rag_service.py             ← hybrid retrieval (Qdrant + Neo4j)
│   │   ├── metadoc_service.py         ← Meta-Document generation orchestration
│   │   ├── deletion_service.py        ← cascade delete across all stores
│   │   ├── credit_service.py          ← credit accounting + checks
│   │   ├── chat_service.py          ← STORY-026: chat session + history + retrieval orchestration
│   │   ├── graph_query_service.py   ← STORY-029: natural language → Cypher + safety validation
│   │   └── email_service.py         ← STORY-032: transactional email (welcome, low-credits, ingestion-complete)
│   │
│   ├── templates/                     ← HTML email templates (plain Python string functions)
│   │   └── emails/
│   │       ├── welcome.py             ← Welcome email HTML renderer
│   │       ├── low_credits.py         ← Low-credits warning email renderer
│   │       └── ingestion_complete.py  ← Ingestion completion email renderer
│   │
│   ├── adapters/                      ← Adapter Layer: one adapter per external system
│   │   ├── __init__.py
│   │   ├── base.py                    ← BaseAdapter with cleanup()
│   │   ├── docling_adapter.py         ← Document parsing (lazy import)
│   │   ├── openai_adapter.py          ← Embeddings + batching
│   │   ├── anthropic_adapter.py       ← Claude Haiku + Sonnet (lazy import, streaming)
│   │   ├── qdrant_adapter.py          ← Vector store (always filters by tenant_id)
│   │   ├── neo4j_adapter.py           ← Graph DB (always WHERE tenant_id)
│   │   ├── storage_adapter.py         ← Supabase Storage (files)
│   │   └── presidio_adapter.py        ← PII masking
│   │
│   ├── workers/                       ← ARQ background tasks
│   │   ├── __init__.py
│   │   ├── main.py                    ← WorkerSettings + function list
│   │   ├── utils.py                   ← publish_progress(), update_job_status()
│   │   ├── ingestion_tasks.py         ← parse_document, generate_embeddings
│   │   ├── graph_tasks.py             ← extract_entities, write_graph_nodes
│   │   ├── conflict_tasks.py          ← scan_for_conflicts, classify_conflict
│   │   ├── deletion_tasks.py          ← cascade_delete_source, delete_account
│   │   └── metadoc_tasks.py           ← generate_meta_document (streaming)
│   │
│   ├── models/                        ← SQLModel database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── profile.py
│   │   ├── source.py
│   │   ├── conflict.py
│   │   ├── meta_document.py
│   │   ├── credit.py
│   │   ├── job_status.py
│   │   └── chat_session.py          ← STORY-026: multi-turn chat session storage
│   │
│   ├── schemas/                       ← Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── common.py                  ← PaginatedResponse, JobResponse
│   │   ├── ingest.py
│   │   ├── search.py
│   │   ├── conflict.py
│   │   ├── graph.py
│   │   ├── metadoc.py
│   │   └── profile.py
│   │
│   └── core/
│       ├── __init__.py
│       ├── config.py                  ← pydantic-settings + @lru_cache
│       ├── logging.py                 ← structlog setup
│       └── errors.py                  ← ErrorCode + raise_4XX helpers
│
└── tests/
    ├── __init__.py
    ├── conftest.py                    ← Fixtures: db_session, qdrant, neo4j, mock_user
    ├── unit/
    │   ├── __init__.py
    │   └── services/
    │       ├── test_ingestion_service.py
    │       ├── test_conflict_service.py
    │       ├── test_rag_service.py
    │       └── test_credit_service.py
    └── integration/
        ├── __init__.py
        ├── api/
        │   ├── test_ingest_endpoints.py
        │   ├── test_conflict_endpoints.py
        │   ├── test_search_endpoint.py
        │   └── test_health_endpoint.py
        └── workers/
            ├── test_ingestion_tasks.py
            ├── test_graph_tasks.py
            └── test_conflict_tasks.py
```

---

## Frontend Repo: `ravenbase-web`

```
ravenbase-web/
│
├── CLAUDE_FRONTEND.md                 ← Frontend agent instructions
├── package.json
├── tsconfig.json                      ← strict: true, no any
├── components.json                    ← shadcn/ui new-york config
├── next.config.mjs
├── postcss.config.mjs
├── .env.local.example
│
├── app/
│   ├── globals.css                    ← Ravenbase tokens + dark/light variables
│   ├── layout.tsx                     ← Root: fonts + ThemeProvider + Analytics
│   ├── (marketing)/                   ← Route group: light mode, no auth
│   │   ├── layout.tsx
│   │   ├── page.tsx                   ← Landing page
│   │   └── pricing/page.tsx
│   ├── (auth)/                        ← Route group: Clerk auth pages
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── onboarding/page.tsx
│   └── (dashboard)/                   ← Route group: dark mode, requires auth
│       ├── layout.tsx                 ← DashboardLayout + Sidebar
│       ├── page.tsx                   ← Redirect to /dashboard/graph
│       ├── graph/page.tsx
│       ├── inbox/page.tsx
│       ├── workstation/page.tsx
│       ├── sources/page.tsx
│       ├── chat/page.tsx             ← STORY-027: conversational memory chat page
│       └── settings/
│           ├── page.tsx
│           ├── profiles/page.tsx
│           └── billing/page.tsx
│
├── components/
│   ├── ui/                            ← shadcn/ui (auto-generated, never edit manually)
│   ├── marketing/                     ← Landing page components
│   │   ├── Header.tsx
│   │   ├── HeroSection.tsx
│   │   ├── WorkflowSection.tsx
│   │   ├── FeaturesSection.tsx
│   │   ├── CTASection.tsx
│   │   └── Footer.tsx
│   └── domain/                        ← App-specific feature components
│       ├── Omnibar.tsx
│       ├── ConflictCard.tsx
│       ├── MemoryInbox.tsx
│       ├── GraphExplorer.tsx
│       ├── GraphNodePanel.tsx
│       ├── IngestionDropzone.tsx
│       ├── IngestionProgress.tsx
│       ├── MetaDocEditor.tsx
│       ├── Workstation.tsx
│       ├── OnboardingWizard.tsx
│       ├── GraphQueryBar.tsx         ← STORY-030: natural language query input + example chips
│       ├── GraphQueryResults.tsx     ← STORY-030: results panel with memory cards + Cypher reveal
│       ├── MemoryChat.tsx            ← STORY-027: main chat client component
│       ├── ChatSessionSidebar.tsx    ← STORY-027: session history list
│       ├── ChatMessage.tsx           ← STORY-027: individual message bubble with citations
│       ├── CitationCard.tsx          ← STORY-027: citation link → graph node navigation
│       ├── ImportFromAIChat.tsx      ← STORY-028: import helper tab
│       └── GeneratedPromptBox.tsx    ← STORY-028: read-only prompt + copy button
│
├── contexts/
│   └── ProfileContext.tsx             ← Active System Profile state
│
├── hooks/
│   ├── use-mobile.ts
│   ├── use-keyboard-inbox.ts          ← J/K/Enter/Backspace/C shortcuts
│   ├── use-optimistic-action.ts       ← Optimistic update + rollback pattern
│   └── use-sse.ts                     ← Server-Sent Events subscription
│
├── lib/
│   ├── utils.ts                       ← cn() helper
│   ├── api.ts                         ← apiFetch() with Clerk token
│   └── api-client/                    ← AUTO-GENERATED from FastAPI OpenAPI (never edit)
│
└── middleware.ts                      ← Clerk auth middleware (protects /dashboard/*)
```

---

## File Naming Conventions

| Type | Convention | Example |
|---|---|---|
| React components | PascalCase | `ConflictCard.tsx` |
| Hooks | `use-kebab-case.ts` | `use-keyboard-inbox.ts` |
| Contexts | PascalCase + Context | `ProfileContext.tsx` |
| Page files | `page.tsx` (Next.js convention) | `app/(dashboard)/graph/page.tsx` |
| Python modules | `snake_case.py` | `ingestion_service.py` |
| Python classes | PascalCase | `IngestionService` |
| Python functions | `snake_case` | `parse_and_chunk()` |
| DB tables | plural snake_case | `system_profiles` |
| Constants | SCREAMING_SNAKE_CASE | `MAX_FILE_SIZE_FREE` |
