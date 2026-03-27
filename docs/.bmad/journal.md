# Ravenbase — Project Development Journal

> **Agent instruction:** This is an append-only log. NEVER edit past entries.
> After every completed story, add one new entry following the template below.
> Add it under the correct Sprint section. If the sprint section does not exist yet,
> create it. Commit this file together with `docs/stories/epics.md` and
> `docs/.bmad/project-status.md` in the "docs: mark STORY-XXX complete" commit.

---

## Project Stats

| Field | Value |
|---|---|
| Total stories complete | 8 / 37 |
| Current phase | Phase A — Backend (Sprints 1–17) |
| Current sprint | 7 |
| Active repo | ravenbase-api |
| Project started | 2026-03-25 |
| Last entry | 2026-03-27 (STORY-010) |

> **Update this table** after every story entry. Increment stories complete,
> update current sprint and phase when they change.

---

## How to Write an Entry

Copy this template and fill in all fields. Never leave a field blank — use "None"
if genuinely nothing to report.

```
### STORY-XXX — [Title]
**Date:** YYYY-MM-DD | **Sprint:** N | **Phase:** A or B | **Repo:** ravenbase-api or ravenbase-web
**Quality gate:** ✅ clean  OR  ⚠️ passed with warnings  OR  ❌ failed (describe fix)
**Commit:** `xxxxxxxx`  ← first 8 chars of git commit hash

**What was built:**
1–3 sentences. What exists now that did not exist before.

**Key decisions:**
Bullet points. Any non-obvious architectural choice made during this story and the
reason behind it. These are the entries most valuable to future agents and to you
when debugging months later. If you followed the story spec exactly with no
deviations, write "Implemented per spec — no deviations."

**Gotchas:**
Bullet points. Non-obvious behaviors, library quirks, environment surprises,
or things that took longer than expected. If none, write "None."

**Tech debt noted:**
Bullet points. Anything deferred, implemented suboptimally, or that should be
revisited in a later story. If none, write "None."
```

---

## Sprint 1 — Foundation

> Backend scaffolding: repos, Docker, databases, ARQ worker, health endpoint.
> Sprints 1 covers STORY-001 and STORY-002.

### STORY-001 — API and Web Repo Scaffolding
**Date:** 2026-03-25 | **Sprint:** 1 | **Phase:** A | **Repo:** ravenbase-api + ravenbase-web
**Quality gate:** ✅ clean
**Commit:** `4fee9e9`

**What was built:**
Scaffolded both ravenbase-api and ravenbase-web from scratch. API: FastAPI app with `/health` endpoint, full Python package structure, pyproject.toml + uv.lock, Makefile, three Docker Compose configs, ARQ worker stub, Alembic config, and test fixtures. Web: Next.js 15 App Router with Tailwind v4 design tokens, three Google fonts, brand components (RavenbaseLogo 5 sizes + RavenbaseLockup), shadcn/ui Button, error pages, and admin/dashboard route groups.

**Key decisions:**
- CORS set to localhost:3000 for dev and ravenbase.app for prod, respecting deployment environments
- Used lifespan context manager pattern (FastAPI 0.93+) for ARQ pool and database lifecycle
- structlog configured with environment branching: ConsoleRenderer in dev, JSONRenderer in prod
- Alembic initialized in autogenerate mode for schema migrations

**Gotchas:**
- uv.lock must be committed to git (not .gitignore'd) to ensure reproducible dependency resolution
- FastAPI lifespan pattern requires Python 3.10+ async context manager syntax
- CORS middleware order matters; must be applied before route registration

**Tech debt noted:**
None.

### STORY-002 — PostgreSQL Schema + Alembic Migrations
**Date:** 2026-03-25 | **Sprint:** 1 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean
**Commit:** `39fa3c9`

**What was built:**
All 8 SQLModel table classes (`User`, `SystemProfile`, `Source`, `SourceAuthorityWeight`, `Conflict`, `MetaDocument`, `CreditTransaction`, `JobStatus`) with correct field types, defaults, indexes, and foreign keys. Alembic autogenerate migration created and applied (`234dbe10`). Two composite indexes added for query performance: `idx_sources_user_ingested` and `idx_conflicts_user_status_created`. 8 unit tests + 3 integration tests all passing.

**Key decisions:**
- Used async Alembic pattern (`asyncio.run` + `async_engine_from_config` + `connection.run_sync`) because `DATABASE_URL` uses `+asyncpg` driver; sync pattern (psycopg2) is not installed.
- Source composite index uses `ingested_at` (not `created_at`) — Source model has no `created_at` field; plan had a naming mismatch.
- `MetaDocument` uses PostgreSQL-specific `JSONB` + `ARRAY(String)` column types via `sa_column=Column(...)` — unit tests validate Python-level instantiation only, not DB types.
- `CreditTransaction.id` is an int (BIGSERIAL) not UUID — credit ledger uses sequential integer PKs for ordering guarantees.
- All `__tablename__` assignments suppressed with `# type: ignore[assignment]` — known pyright false positive with SQLModel.
- All `Optional[X]` rewritten to `X | None` (ruff UP045) for Python 3.10+ compatibility.

**Gotchas:**
- `asyncpg` and `greenlet` were missing from `pyproject.toml` (STORY-001 gap) — had to add both before `alembic upgrade head` would work.
- `alembic/script.py.mako` was missing (STORY-001 gap) — had to copy from `.venv/lib/python3.13/site-packages/alembic/templates/async/script.py.mako`.
- `alembic.ini` is inside `alembic/` directory, not project root — must use `uv run alembic -c alembic/alembic.ini ...`.
- `.envs/.env.dev` points to Supabase production DB; local Docker uses `ravenbase:ravenbase@localhost:5432/ravenbase` — override via `DATABASE_URL=...` env var prefix when running alembic locally.
- Auto-generated migration file referenced `sqlmodel.sql.sqltypes.AutoString` without importing `sqlmodel` — caused `NameError` at upgrade time; fixed by adding `import sqlmodel  # noqa: F401`.
- Docker postgres credentials are `ravenbase/ravenbase` (from `docker-compose.yml POSTGRES_USER: ravenbase`), not the default `postgres/postgres`.

**Tech debt noted:**
- Integration tests require local Docker postgres and `DATABASE_URL` env override — not wired into `make test` yet. Consider adding a `make test-integration` target that sets the correct URL.

---

## Sprint 2 — Storage Adapters + Worker

> Qdrant collection setup, Neo4j constraints, ARQ worker configured.
> Sprint 2 covers STORY-003 and STORY-004.

### STORY-003 — Qdrant + Neo4j Initialization + Constraints
**Date:** 2026-03-26 | **Sprint:** 2 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean
**Commit:** `6750b5f`

**What was built:**
`QdrantAdapter` (`src/adapters/qdrant_adapter.py`) with `search()`, `upsert()`, `delete_by_filter()`, `count()`, `verify_connectivity()`, and a `_tenant_filter()` helper that enforces tenant isolation on every query. `Neo4jAdapter` (`src/adapters/neo4j_adapter.py`) with `run_query()`, `write_nodes()`, `write_relationships()`, and `verify_connectivity()` — all Cypher uses parameterized `tenant_id`. Idempotent setup scripts (`scripts/setup_qdrant.py`, `scripts/setup_neo4j.py`) with `make setup-qdrant` and `make setup-neo4j` Makefile targets. `/health` endpoint upgraded to check all 4 services in parallel. `mock_qdrant` and `mock_neo4j` fixtures added to `tests/conftest.py`.

**Key decisions:**
- `_tenant_filter()` is a private method on `QdrantAdapter`, not a free function — prevents callers from bypassing it; every public query method calls it internally.
- `Neo4jAdapter.run_query()` accepts `**params` and always passes them through to the driver — no string interpolation path exists by design.
- Both adapters store `None` in `__init__` and open connections lazily via `_get_client()` / `_get_driver()` — satisfies RULE 6 (fast `__init__`).
- Qdrant collection uses `on_disk_payload=True` + sparse BM25 vectors for hybrid search as specified in architecture docs.
- Neo4j setup script creates 4 uniqueness constraints and 1 index using `IF NOT EXISTS` Cypher so it is idempotent.
- `/health` uses `asyncio.gather()` to check all 4 services concurrently — degraded status returned (not 500) when any check fails.

**Gotchas:**
- `ruff format` found 3 files that needed reformatting (`qdrant_adapter.py`, `test_health_endpoint.py`, `test_qdrant_adapter.py`) — auto-fixed before committing.
- 3 STORY-002 integration tests (`test_database_connectivity.py`) fail when run offline because they resolve the Supabase cloud hostname. These are pre-existing and not regressions from STORY-003.

**Tech debt noted:**
- `make test` includes the Supabase-dependent connectivity tests with no skip marker; consider adding `@pytest.mark.requires_db` and a `--skip-cloud` pytest flag to cleanly separate local-only from cloud-dependent tests.

### STORY-004 — ARQ Worker Setup + Health Endpoint
**Date:** 2026-03-26 | **Sprint:** 2 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean
**Commit:** `4976e52`

**What was built:**
`src/workers/utils.py` with `publish_progress()` (async Redis pub/sub, `job:progress:{source_id}` channel) and `update_job_status()` (opens its own `AsyncSession` per call, updates `JobStatus` record with status/progress/message/updated_at). `src/workers/main.py` completed with `hello_world` stub task and full `WorkerSettings` (job_timeout, keep_result, retry_jobs, max_tries, health_check_interval, health_check_key). 5 new unit tests; 36 total pass. 100% coverage on both new files.

**Key decisions:**
- `publish_progress` opens and closes its own Redis connection per call (matches architecture doc pattern). The ARQ `ctx["redis"]` pool approach would be more efficient at scale but requires threading the context through — deferred to STORY-006 when the first real task uses this utility.
- `update_job_status` uses `async_session_factory` from `src/api/dependencies/db.py` directly (not `get_db` which is a FastAPI dependency). This is a minor layer boundary concern; can be moved to `src/core/db.py` if needed later.
- Removed `cron_jobs: list = []` from WorkerSettings — ARQ doesn't require explicit empty declaration and it added unnecessary type-ignore noise.
- `ctx` parameter renamed to `_ctx` in `hello_world` to satisfy ruff ARG001 (unused arg).

**Gotchas:**
- `aioredis.from_url` is an `async def` — patching it with `MagicMock(return_value=mock)` doesn't work; must use `async def fake_from_url(_url): return mock` as the patch target.
- ruff flags unused `ctx` argument in ARQ task functions — prefix with `_` to silence.
- ruff format auto-reformatted inline comments (trailing `# ...` on assignment lines) to use 2-space separation.

**Tech debt noted:**
- `publish_progress` creates a new Redis TCP connection per call. When STORY-006 implements `parse_document`, pass `ctx["redis"]` instead to reuse the ARQ-managed connection pool.

---

## Sprint 3 — File Upload

> Supabase Storage integration, MIME validation, deduplication, rate limiting.
> Sprint 3 covers STORY-005.

### STORY-005 — File Upload Endpoint + Supabase Storage
**Date:** 2026-03-26 | **Sprint:** 3 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ 42 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `2dbbf64`

**What was built:**
`POST /v1/ingest/upload` endpoint: accepts multipart/form-data, runs MIME validation, file size enforcement (50 MB free / 200 MB pro), SHA-256 deduplication, Supabase Storage upload at `/{tenant_id}/{source_id}/{filename}`, PostgreSQL `Source` record creation, and ARQ job enqueue — all returning 202 immediately. `StorageAdapter`, `IngestionService`, and a `process_ingestion` stub task added. ARQ pool initialised in FastAPI lifespan and stored on `app.state`. Rate limiting via Redis INCR/EXPIRE on `rate_limit:{tenant_id}:upload`.

**Key decisions:**
- `import magic` kept lazy inside `validate_file_type` — `python-magic` requires the system `libmagic` shared library which may not be installed in all environments (CI, dev machines without Homebrew). Lazy import fails loudly at call time, not at startup.
- `app.state.arq_pool` set directly in test fixtures rather than mocking `create_pool` — `ASGITransport` (httpx) does not trigger the ASGI lifespan handler, so the lifespan is never called during tests. Setting `app.state.arq_pool` directly is the correct workaround.
- `get_db` overridden via `app.dependency_overrides` with an async generator function (not `lambda: gen_object`) — FastAPI's DI resolves generator dependencies by calling the override function and iterating; a lambda returning a generator object is not iterated correctly.
- `tier` extracted from `payload["public_metadata"]["plan"]` in `require_user` — Clerk embeds subscription tier in JWT `public_metadata`; defaulting to `"free"` ensures backward compatibility if the claim is absent.
- `python-multipart` added to runtime dependencies — FastAPI requires it to process `UploadFile` / multipart form data; it was missing from `pyproject.toml`.

**Gotchas:**
- `ASGITransport` does not call the ASGI lifespan scope — every test using `app.state` must set state directly before making requests.
- `mocker.patch("src.services.ingestion_service.magic.from_buffer")` fails when `import magic` is lazy: the attribute doesn't exist on the module until the function is called. Solution: patch at the method level (`mocker.patch.object(IngestionService, "validate_file_type", ...)`) instead.
- Dependency override `lambda: _mock_db_gen(mock_db)` does NOT work — returns the async generator object, which FastAPI doesn't iterate. Must use a named `async def` function that `yield`s the mock.
- `ruff format` reformatted `ingestion_service.py` and `test_ingest_upload.py` after initial write — always run `ruff format` before the quality check.

**Tech debt noted:**
- `validate_file_type` unit tests (testing actual `magic.from_buffer` behaviour against real PDF/DOCX/text bytes) are absent because `libmagic` is not installed on the dev machine. Add a `@pytest.mark.requires_libmagic` marker and run these in CI where `libmagic` is available via apt/brew.
- `check_rate_limit` opens a new `aioredis` connection per call — same pattern as `publish_progress` in STORY-004. Refactor both to accept an optional `redis` client parameter so ARQ workers can pass `ctx["redis"]` in STORY-006.

---

## Sprint 4 — Docling Pipeline

> PDF parsing, chunking, embedding, Qdrant upsert, content moderation.
> Sprint 4 covers STORY-006.

### STORY-006 — Docling Parse + Chunk + Embed Worker
**Date:** 2026-03-26 | **Sprint:** 4 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 58 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `94f47d2`

**What was built:**
Full ARQ `parse_document` pipeline replacing the STORY-005 stub. New adapters: `DoclingAdapter` (lazy Docling imports, paragraph-aware chunking with overlap in a thread executor), `OpenAIAdapter` (batched `text-embedding-3-small` embeddings in groups of 100), `ModerationAdapter` (OpenAI moderation pre-check before Docling, raises `ModerationError` with `hard` flag). `StorageAdapter.download_file()` added. `ingestion_tasks.py` implements the full status pipeline: PENDING→PROCESSING→INDEXING→COMPLETED with Redis pub/sub progress events. Qdrant upsert uses deterministic UUIDs (`uuid.uuid5`) so re-runs are safe. Graph extraction is enqueued as the final step.

**Key decisions:**
- Docling `DocumentConverter.convert()` takes a `DocumentStream(name, stream)` — not `convert_from_bytes()` which does not exist in the installed version. Unit tests updated to mock `convert` (not `convert_from_bytes`) and to include `docling_core.types.io` in the `sys.modules` patch dict.
- `_update_source_status` typed as `status: str` (not `status: SourceStatus`) because `SourceStatus` is a plain namespace class (not an Enum), and `Source.status` is a `str` field — pyright correctly rejects the mismatch.
- `_extract_text_preview` extracts readable text before Docling for the moderation pre-check, using plain bytes/zip parsing (no heavy ML) so it is synchronous and fast.
- Moderation hard-rejects deactivate the user account (`user.is_active = False`) and do not retry; soft-rejects only mark the source as FAILED.
- `ruff format` was required after initial file writes — 6 files reformatted before `make quality` passed.

**Gotchas:**
- `ruff check` flagged `PLC0415` (import not at top level) and `I001` (unsorted imports) in `test_storage_adapter_download.py` — fixed by moving `import pytest` before `unittest.mock` and adding `# noqa: PLC0415` on in-function imports.
- Pyright error on `source.status = status` when `status: SourceStatus` — pyright infers `SourceStatus` as a class type, not a string, so assigning to `str` field fails. Fix: type annotation changed to `str`.
- `test_parse_and_chunk_*` tests returned empty lists after the `convert_from_bytes` → `convert` change because the mock still wired `convert_from_bytes`. Updated `_make_docling_sys_modules` helper to wire `mock_conv_instance.convert.return_value` and added `docling_core.types.io` stub.

**Tech debt noted:**
- `parse_document` opens separate DB sessions for each status transition (`_update_source_status`, `_set_source_completed`, `_set_source_failed`). These could be batched or merged in a later refactor if DB round-trips become a bottleneck.
- `graph_extraction` task is enqueued by name (`"graph_extraction"`) but not yet implemented — will silently fail in ARQ until STORY-009. This is intentional per spec.

---

## Sprint 5 — SSE + Text Ingest

> Progress streaming, Omnibar text capture endpoint.
> Sprint 5 covers STORY-007-BE and STORY-008-BE.

### STORY-007 Part 1 — SSE Progress Stream (Backend)
**Date:** 2026-03-26 | **Sprint:** 5 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 68 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `bd3c17b`

**What was built:**
`GET /v1/ingest/stream/{source_id}?token=<jwt>` SSE endpoint using `sse-starlette`. `verify_token_query_param(token: str = Query(...))` FastAPI dependency added for EventSource auth (EventSource cannot set request headers). `_decode_jwt()` private helper extracted to share JWT validation logic between `require_user` and the new dependency. `ProgressEvent` Pydantic schema added to `src/schemas/ingest.py`. 10 new tests (4 unit + 6 integration), all 68 tests passing.

**Key decisions:**
- `verify_token_query_param` uses `Query(...)` not `Header(None)` — browser `EventSource` API cannot set custom headers, so the Clerk JWT must travel as a URL query parameter.
- `_decode_jwt()` extracted as a private helper to keep `require_user` and `verify_token_query_param` DRY. Both are now one-line delegators.
- `except BaseException: pass` removed from the generator — `try/finally` alone guarantees cleanup on `GeneratorExit`. The bare-except pattern silently swallowed all exceptions including real bugs; discovered during code quality review.
- `json.loads(payload)` wrapped in `try/except json.JSONDecodeError` with a `log.warning` — a malformed worker payload should log and continue, not crash the stream.
- Disconnect test uses `raise Exception(...)` in the mock async generator (not `raise GeneratorExit`) — `GeneratorExit` propagated through `sse_starlette`'s internal `TaskGroup` as a `BaseExceptionGroup`, crashing the test boundary. A regular exception correctly exercises the `try/finally` cleanup path without this side effect.
- `except jwt.PyJWTError` used instead of bare `except Exception` in `_decode_jwt` — catches all PyJWT validation errors without swallowing unrelated programming errors.

**Gotchas:**
- `sse-starlette` wraps the generator in an `anyio.TaskGroup`. Raising `GeneratorExit` inside a mock `async for` body escapes as a `BaseExceptionGroup` at the httpx client boundary — not catchable by `except Exception`. Switched the disconnect simulation to a plain `Exception` which is handled gracefully.
- `app.dependency_overrides.pop(verify_token_query_param, None)` mid-test (for the 422 test) needed a `try/finally` restore block to avoid leaking the removal when the assertion fails.

**Tech debt noted:**
- `verify_token_query_param` currently does not validate that the `tenant_id` from the JWT matches the owner of `source_id` in the database. A future security hardening story should add a DB lookup to confirm the caller owns the source before subscribing to its Redis channel.

### STORY-008 Part 1 — Text Quick-Capture (Backend)
**Date:** 2026-03-26 | **Sprint:** 5 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 70 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `5c543f2`

**What was built:**
`POST /v1/ingest/text` endpoint accepting `{content, profile_id, tags}` JSON body. `TextIngestRequest` Pydantic schema added. `IngestionService.handle_text_ingest()` validates 50,000-char limit (raises `TEXT_TOO_LONG`), SHA-256 deduplication, creates Source record with `file_type="direct_input"` and `storage_path="direct_input"` (non-nullable sentinel), enqueues `ingest_text` ARQ task. `ingest_text` worker task: plain-text chunking (2000-char chunks, 200-char overlap), OpenAI `text-embedding-3-small` embeddings, Qdrant upsert with deterministic UUIDs, PENDING → PROCESSING → INDEXING → COMPLETED status transitions, Redis pub/sub progress events, graph_extraction enqueued on completion. 2 integration tests added.

**Key decisions:**
- `Source.storage_path` is non-nullable (`str`) — used sentinel `"direct_input"` to avoid a DB migration.
- Chunking is character-based (2000 chars, 200 overlap) rather than token-based — simpler and sufficient for the 50k char cap.
- Tags stored in Qdrant payload only (no Source model column) — avoids schema change and keeps tags searchable via vector filter.
- No content moderation for direct-input text — YAGNI at this stage; story scope doesn't require it.

**Gotchas:**
- None encountered — straightforward implementation following `parse_document` pattern.

**Tech debt noted:**
- Tags are not persisted to PostgreSQL — a future story may want a `source_tags` join table if tag-based filtering at the DB layer (not just Qdrant) becomes necessary.

---

## Sprint 6 — SSE Frontend + Omnibar UI

> IngestionProgress component, Omnibar quick-capture UI.
> Sprint 6 covers STORY-007-FE and STORY-008-FE.

_No entries yet._

---

## Sprint 7 — Entity Extraction + Graph API

> LLMRouter (Gemini Flash + Haiku fallback), Neo4j writer, graph endpoints.
> Sprint 7 covers STORY-009 and STORY-010.

### STORY-009 — Entity Extraction + Neo4j Writer
**Date:** 2026-03-26 | **Sprint:** 7 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — all tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `ada81c3`

**What was built:**
LLMRouter adapter routing entity_extraction to Gemini 2.5 Flash (primary) and Claude Haiku (fallback) with exponential backoff on 429. GraphService orchestrating per-chunk entity extraction via LLM and MERGE writes to Neo4j for Concept nodes (deduplication by {name, tenant_id}) and CREATE for Memory nodes. graph_extraction ARQ task wired into WorkerSettings, triggered automatically by parse_document and ingest_text. QdrantAdapter.scroll_by_source for paginated chunk retrieval.

**Key decisions:**
Used MERGE (c:Concept {name: $name, tenant_id: $tenant_id}) with ON CREATE SET / ON MATCH SET to deduplicate concepts across re-ingestions while keeping created_at immutable and updating updated_at on each match. Confidence threshold 0.6 filters low-quality extractions before Neo4j writes. litellm imported lazily (RULE 6). User-controlled chunk content wrapped in XML boundary tags (RULE 10). Chunk failures logged and skipped — one bad LLM call does not abort the entire source graph write.

**Gotchas:**
ON CREATE SET in MERGE clause uses the word "CREATE" as a substring — test assertion for "Concepts must use MERGE not CREATE" must use startsWith("MERGE") not absence-of-"CREATE" to avoid false negatives.

**Tech debt noted:**
GraphService._write_to_neo4j issues N separate run_query calls per chunk (1 per entity + 1 per memory + N relationship queries). For sources with hundreds of chunks and many entities, this could be batched with UNWIND for better Neo4j throughput.

---

### STORY-010 — Graph API Endpoints (nodes + neighborhood)
**Date:** 2026-03-27 | **Sprint:** 7 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 102 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `3cb5040`

**What was built:** Graph API endpoints for the Graph Explorer UI. `GET /v1/graph/nodes` returns all tenant-scoped nodes and edges (with optional `profile_id` and `node_types` filters, default limit 200). `GET /v1/graph/neighborhood/{node_id}` returns an N-hop subgraph (default hops=2, limit=50). Added `GraphNode`, `GraphEdge`, `GraphResponse` Pydantic schemas to `src/schemas/graph.py`. Added `get_nodes_for_explorer()` and `get_neighborhood()` to `GraphService` with private helpers for node ID/label extraction, deduplication, and `memory_count` computation. 12 integration tests (schema, service, endpoint layers).

**Key decisions:** Used two separate Cypher queries for neighborhood (nodes then relationships with DISTINCT) to avoid cartesian product from UNWIND. Returned `labels(n)[0]` and `type(r)` as scalars in queries so `run_query()` dicts carry full metadata without adapter changes. Profile filter uses `n.profile_id` property (written by STORY-009) — not the non-existent HAS_MEMORY → SystemProfile relationship. Route handlers use `with GraphService() as svc:` context manager for proper adapter cleanup.

**Gotchas:** STORY-010 story doc referenced a HAS_MEMORY relationship from Memory to SystemProfile that was never created — profile filter corrected to property-based. Cypher `result.data()` loses node labels and relationship types; workaround is explicit `labels(n)[0]` / `type(r)` in RETURN clause.

**Tech debt noted:** Concept nodes do not carry profile_id; profile filter only applies to Memory nodes. A future story should add profile-scoped Concept traversal if needed.

---

## Sprint 8 — Graph Explorer UI

> Cytoscape.js force-directed graph, node detail panel, mobile degradation.
> Sprint 8 covers STORY-011.

_No entries yet._

---

## Sprint 9 — Conflict Detection + Resolution API

> Qdrant similarity scan, conflict classification, resolve/undo endpoints.
> Sprint 9 covers STORY-012 and STORY-013.

_No entries yet._

---

## Sprint 10 — Memory Inbox UI

> Keyboard-driven triage, 3 flows (binary, conversational, auto-resolved).
> Sprint 10 covers STORY-014.

_No entries yet._

---

## Sprint 11 — Hybrid Retrieval + Meta-Doc Generation

> RAG pipeline, Presidio PII masking, SSE streaming generation.
> Sprint 11 covers STORY-015 and STORY-016.

_No entries yet._

---

## Sprint 12 — Workstation UI

> Streaming Markdown editor, export, auto-save indicator.
> Sprint 12 covers STORY-017.

_No entries yet._

---

## Sprint 13 — Auth Backend

> Clerk JWT validation, webhook handler, User record creation.
> Sprint 13 covers STORY-018-BE.

_No entries yet._

---

## Sprint 14 — Credits System

> Credit ledger, deduction per operation, 402 enforcement.
> Sprint 14 covers STORY-023.

_No entries yet._

---

## Sprint 15 — GDPR + PII Masking

> Full cascade deletion, Presidio entity consistency, 60s SLA.
> Sprint 15 covers STORY-024 and STORY-025.

_No entries yet._

---

## Sprint 16 — Chat Backend + Import Prompt

> Chat SSE streaming, multi-turn sessions, AI import helper endpoint.
> Sprint 16 covers STORY-026 and STORY-028-BE.

_No entries yet._

---

## Sprint 17 — Graph Query Backend

> NL → Cypher via LLMRouter, safety validation, read-only enforcement.
> Sprint 17 covers STORY-029.

_No entries yet._

---

## ✅ Backend Gate Checkpoint

_This section is filled in when all 17 backend sprints are complete._

**Date passed:** _not yet_
**`make test` result:** _not yet_
**`make quality` result:** _not yet_
**`npm run generate-client` result:** _not yet_

---

## Sprint 18 — Web Scaffold

> Next.js 15 App Router, design tokens, shadcn/ui, font system.
> Sprint 18 covers STORY-001-WEB.

_No entries yet._

---

## Sprint 19 — Auth Frontend

> Clerk SignIn/SignUp, JWT on API requests, dashboard middleware.
> Sprint 19 covers STORY-018-FE.

_No entries yet._

---

## Sprint 20 — Onboarding + Profile Switching

> 3-step wizard, GettingStartedChecklist, profile context.
> Sprint 20 covers STORY-019 and STORY-020.

_No entries yet._

---

## Sprint 21 — Chat UI + Import Helper UI

> Token streaming with cursor, citations, session sidebar.
> Sprint 21 covers STORY-027 and STORY-028-FE.

_No entries yet._

---

## Sprint 22 — Graph Explorer UI

> Cytoscape.js, node detail panel, first-run empty states.
> Sprint 22 covers STORY-011.

_No entries yet._

---

## Sprint 23 — Memory Inbox UI

> Keyboard triage, 3 flows, optimistic updates, swipe gestures.
> Sprint 23 covers STORY-014.

_No entries yet._

---

## Sprint 24 — Workstation UI

> Streaming Markdown, export, auto-save ◆ status indicator.
> Sprint 24 covers STORY-017.

_No entries yet._

---

## Sprint 25 — Landing Page + Pricing + Stripe

> 9-section marketing page, Stripe Checkout, webhook idempotency.
> Sprint 25 covers STORY-021 and STORY-022.

_No entries yet._

---

## Sprint 26 — Graph Query Bar

> NL query bar in Graph Explorer, amber node highlighting.
> Sprint 26 covers STORY-030.

_No entries yet._

---

## Sprint 27 — Dark Mode + Email + Legal

> Theme toggle, transactional email, Privacy/Terms pages.
> Sprint 27 covers STORY-031, STORY-032, and STORY-033.

_No entries yet._

---

## Sprint 28 — Dark Mode

> See Sprint 27.

---

## Sprint 29 — Legal Pages

> See Sprint 27.

---

## Sprint 30 — Referral System

> Dual-sided credits, ReferralTransaction table, Settings UI.
> Sprint 30 covers STORY-034.

_No entries yet._

---

## Sprint 31 — Data Export

> ZIP export ARQ job, Supabase Storage, GDPR Article 20.
> Sprint 31 covers STORY-035.

_No entries yet._

---

## Sprint 32 — Email System (continued)

> See Sprint 27.

---

## Sprint 33 — Referral System (continued)

> See Sprint 30.

---

## Sprint 34 — Admin Dashboard

> Cross-repo story: 5 admin API endpoints + admin UI with credit adjustment.
> Sprint 34 covers STORY-036 (backend + frontend).

_No entries yet._

---

## Sprint 35 — Cold Data Lifecycle

> Inactivity CRON, activity middleware, 150/180-day purge.
> Sprint 35 covers STORY-037.

_No entries yet._

---

## ✅ Project Complete Checkpoint

_Filled in when all 37 stories are done._

**Date completed:** _not yet_
**Total duration:** _not yet_
**Total stories:** 37 / 37
**Hardest story (most sessions):** _fill in_
**Biggest surprise:** _fill in_
**Most important architectural decision:** _fill in_
