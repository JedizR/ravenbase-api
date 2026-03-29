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
| Total stories complete | 19 / 37 |
| Current phase | Phase A — Backend (Sprints 1–18) |
| Current sprint | 18 |
| Active repo | ravenbase-api |
| Project started | 2026-03-25 |
| Last entry | 2026-03-29 (STORY-036-BE) |

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

### STORY-012 — Conflict Detection Worker
**Date:** 2026-03-27 | **Sprint:** 9 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean
**Commit:** `45f2c16`

**What was built:**
Qdrant similarity scan (cosine threshold 0.87, always tenant-scoped via `_tenant_filter`) identifies candidate contradiction pairs after each ingestion. LLM classification via `LLMRouter("conflict_classification")` routes to Gemini 2.5 Flash (primary) / Claude Haiku (fallback) and returns `{classification, confidence, reasoning}` validated by `ConflictClassificationResult`. CONTRADICTION/UPDATE pairs create `Conflict` PostgreSQL records; COMPLEMENT pairs write `TEMPORAL_LINK` Neo4j edges only. Auto-resolution fires when challenger authority weight exceeds incumbent by ≥3 points. Redis pub/sub notification published on `conflict:new:{tenant_id}` after DB commit. Batch capped at 5 to prevent notification fatigue. 111 tests passing.

**Key decisions:**
- Retry suppression (no re-raise in `scan_for_conflicts` task): conflict detection is best-effort — a transient failure is non-critical and retrying risks duplicate Conflict records if the first attempt partially succeeded. Consistent with `graph_tasks.py` design.
- `scroll_by_source_with_vectors()` added to `QdrantAdapter` to fetch chunk vectors without re-embedding — avoids OpenAI API cost on every conflict scan.
- `_find_candidates()` uses Qdrant `must_not` filter on `source_id` to exclude self-matches; `search()` signature extended with optional `score_threshold` and `must_not` forwarding.
- RULE 10 compliance: `<statement_a>` / `<statement_b>` XML tags wrap incumbent/challenger text in the classification prompt.

**Gotchas:**
- Local postgres uses `TIMESTAMP WITHOUT TIME ZONE`; `Conflict.created_at` default factory uses `datetime.now(UTC)` (tz-aware). Integration tests must patch `src.models.conflict.datetime` to return naive UTC — same pattern as ingestion tests.
- `arq_ctx = {}` in existing `test_graph_tasks.py` fixtures broke when `graph_extraction` gained the `ctx["redis"].enqueue_job(...)` call. Updated fixture to include `{"redis": MagicMock(enqueue_job=AsyncMock())}`.
- `AsyncQdrantClient` uses `query_points()` (not `search()`); pyright enforces this. Score threshold is supported as a `query_points` parameter.

**Tech debt noted:**
- `_publish_conflict_notification()` opens a fresh Redis connection per call rather than reusing the ARQ worker's `ctx["redis"]` pool. Future refactor: inject `redis_client` into `ConflictService.__init__` alongside `qdrant`, `neo4j`, `llm_router`.
- `_load_authority_weight_by_type` opens a second DB session inside the outer session loop. Could be consolidated to one session per batch.

### STORY-013 — Conflict API (List, Resolve, Undo)
**Date:** 2026-03-27 | **Sprint:** 9 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 126 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `fd35d8c`

**What was built:**
Three REST endpoints exposing the conflict resolution workflow: `GET /v1/conflicts` (paginated, optional `status` filter, newest first); `POST /v1/conflicts/{id}/resolve` supporting ACCEPT_NEW (atomic SUPERSEDES Neo4j edge + `is_valid` flags in one `run_query` call), KEEP_OLD (status-only), and CUSTOM (LLMRouter `custom_resolution` task → `GraphMutations` schema → optional SUPERSEDES edge); `POST /v1/conflicts/{id}/undo` (30-second window, reverses SUPERSEDES + `is_valid` for ACCEPT_NEW). Ownership checks on every mutation (403). `raise_403`, `raise_409` helpers added to `errors.py` with `-> NoReturn` type annotation. `custom_resolution` task added to `_TASK_ROUTING` in `llm_router.py`.

**Key decisions:**
- `-> NoReturn` on all `raise_*` helpers in `errors.py` — pyright cannot infer that HTTPException-raising helpers never return, causing false "attribute of None" errors on every post-raise access. `NoReturn` fixes this without guard assertions.
- ACCEPT_NEW uses a single `run_query` Cypher (MATCH + MATCH + MERGE + SET) rather than separate `write_relationships` + `write_nodes` calls — ensures the SUPERSEDES edge and `is_valid` flag changes are atomic in one Neo4j session.
- `custom_resolution` routes to Gemini 2.5 Flash + Haiku fallback (same as `conflict_classification`) — it's a background-style synthesis task, not user-facing streaming, so the cost-optimized tier is appropriate.
- FastAPI dependency override in tests must use a named `async def _db_override(): yield mock_db` function, not `lambda: _mock_db_gen(mock_db)`. The lambda pattern returns an async generator object directly; FastAPI does not automatically iterate it when used as an override.

**Gotchas:**
- `StrEnum` (Python 3.11+) required instead of `class Foo(str, Enum)` — ruff UP042 rule rejects the old pattern. Schemas file uses `from enum import StrEnum`.
- `PaginatedResponse` re-export in `schemas/conflict.py` triggered ruff PLC0414 (alias doesn't rename). Fixed with `# noqa: PLC0414` comment.
- `_CUSTOM_PROMPT` as a local variable in `_apply_custom_resolution` triggers ruff N806 (function variables should be lowercase). Moved to module level as `_CUSTOM_RESOLUTION_PROMPT`.

**Tech debt noted:**
- CUSTOM resolution applies LLM-suggested `GraphMutations` but does not attempt to reverse them on undo (only status is reset). A future story could store the mutations JSON in `Conflict.resolution_note` for reversibility.
- `ConflictService` is instantiated fresh per request in route handlers. Could use a request-scoped singleton via FastAPI's dependency injection if adapter init latency becomes measurable.

---

## Sprint 10 — Memory Inbox UI

> Keyboard-driven triage, 3 flows (binary, conversational, auto-resolved).
> Sprint 10 covers STORY-014.

_No entries yet._

---

## Sprint 11 — Hybrid Retrieval + Meta-Doc Generation

> RAG pipeline, Presidio PII masking, SSE streaming generation.
> Sprint 11 covers STORY-015 and STORY-016.

### STORY-015 — Hybrid Retrieval Service
**Date:** 2026-03-27 | **Sprint:** 11 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 158 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `cade520`

**What was built:**
RAGService with three-phase retrieval pipeline: (1) Qdrant kNN semantic search with tenant+profile scoping, (2) Neo4j concept-graph traversal via `find_memories_by_concepts()`, (3) re-ranking with formula `semantic×0.6 + recency×0.3 + profile_match×0.1` and content-hash deduplication. New `embed()` single-text method added to `OpenAIAdapter`. 24 unit tests and 8 integration tests added.

**Key decisions:**
- `is_valid` check uses `IS NULL OR true` to handle Memory nodes written before conflict resolution was in place — avoids filtering out pre-existing nodes that lack the property.
- Profile-scoped Neo4j query uses `m.profile_id = $profile_id` property filter (no `HAS_MEMORY` traversal) — simpler Cypher and avoids adding a relationship type not yet defined in the schema.
- Deduplication by SHA-256 content hash: the same chunk may arrive from both Qdrant and Neo4j; hashing ensures deterministic deduplication regardless of source order.

**Gotchas:**
- `extract_concepts()` filters words shorter than 4 characters and stop-words using a frozenset. Words of exactly 4 characters pass the `len(word) > 3` check — confirmed by tests. The stop-word list must be maintained manually if new common words need filtering.
- Integration tests mock both Qdrant and Neo4j adapters to avoid requiring live infrastructure; async mock setup requires `AsyncMock` not `MagicMock` for coroutine returns.

**Tech debt noted:**
- `retrieve()` currently runs Qdrant search and Neo4j traversal sequentially; these could be parallelised with `asyncio.gather()` in a future performance story.
- BM25 sparse-vector hybrid search is stubbed (Qdrant dense-only for now); STORY-016 or a later story should enable sparse vectors once the Qdrant collection is seeded.

---

### STORY-016 — Meta-Doc Generation Worker + Streaming
**Date:** 2026-03-28 | **Sprint:** 11 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 182 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `73c49bf`

**What was built:**
End-to-end Meta-Document generation pipeline. `POST /v1/metadoc/generate` performs a credit check (402 before enqueueing, deduction only after success) and enqueues an ARQ job. `GET /v1/metadoc/stream/{job_id}` subscribes to Redis pub/sub channel `metadoc:stream:{job_id}` and re-streams SSE events. ARQ worker `generate_meta_document` runs the full pipeline: RAGService hybrid retrieval → optional Presidio PII masking → Anthropic streaming with XML boundary tags → bleach XSS sanitization → PostgreSQL MetaDocument save → Neo4j CONTAINS edges → credit deduction from User + CreditTransaction record → final `done` event. New adapters: `AnthropicAdapter` (lazy import, streaming), `PresidioAdapter` (lazy import, deterministic pseudonymization). 24 new tests added (unit + integration).

| Stat | Count |
|---|---|
| Files created | 7 (schemas, 2 adapters, service, worker, route, tests) |
| Files modified | 5 (neo4j_adapter, errors, auth, api/main, workers/main) |
| Tests added | 24 |
| Total tests | 182 |

**Key decisions:**
- Credit check (402) is in `MetadocService.handle_generate()` before `arq_pool.enqueue_job()`. Credit deduction runs inside the worker after all phases succeed — a worker failure charges nothing.
- `verify_token_query_param` changed from `Query(...)` (422 on missing) to `Query(None)` + explicit 401 raise — semantically correct for auth failures; EventSource clients cannot set Authorization headers.
- `asyncio.timeout(300)` wraps the entire worker pipeline — 5-minute hard cap; on `TimeoutError`, publishes error event and returns `{"status": "timeout"}` without charging credits.
- bleach.clean() import is lazy (`import bleach  # noqa: PLC0415`) inside the worker task to avoid startup overhead (RULE 6).

**Gotchas:**
- `aioredis.from_url()` is synchronous, not a coroutine — `r = aioredis.from_url(url)` (no `await`). The `publish` call is async. Easy to confuse in tests.
- `mocker.patch.object(_settings, "ENABLE_PII_MASKING", True)` is required for patching pydantic-settings fields in worker tests — `mocker.patch("src.core.config.settings.ENABLE_PII_MASKING", ...)` is invalid Python mock syntax.
- `_fake_session_ctx()` in worker tests must be a callable class (not just an async context manager) because `async_session_factory` is called twice in the worker (once for MetaDocument save, once for credit deduction).

**Tech debt noted:**
- `AnthropicAdapter` is used directly in the worker. CLAUDE.md prefers `LLMRouter` for service-layer LLM calls; however, the Anthropic streaming API is not yet supported by LiteLLM's streaming interface in the current version — track for STORY-018-BE refactor.

---

## Sprint 12 — Workstation UI

> Streaming Markdown editor, export, auto-save indicator.
> Sprint 12 covers STORY-017.

_No entries yet._

---

## Sprint 13 — Auth Backend

> Clerk JWT validation, webhook handler, User record creation.
> Sprint 13 covers STORY-018-BE.

### STORY-018-BE — Clerk Auth Integration (Backend)
**Date:** 2026-03-28 | **Sprint:** 13 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean
**Commit:** `a0cbf5a`

**What was built:**
Clerk JWT authentication via PyJWT + JWKS endpoint: `require_user` FastAPI dependency validates RS256 tokens against Clerk's public JWKS URL, caching the `PyJWKClient` in-process. `POST /webhooks/clerk` handler with Svix signature verification creates or updates User records on `user.created` / `user.updated` events. `PresidioAdapter` and `Neo4jAdapter` PII/tenant-isolation fixes landed alongside this story. Auth dependency wired to all existing routes.

**Key decisions:**
- `PyJWKClient` is module-level cached (singleton) — JWKS fetch happens once at first request rather than on every token validation, avoiding latency spikes and rate limiting on Clerk's JWKS endpoint.
- `svix` library used for webhook signature validation — verifies `svix-id`, `svix-timestamp`, and `svix-signature` headers in one call; rejects replays outside the 5-minute tolerance window.
- `require_user` returns `{"user_id": payload["sub"], "email": payload.get("email", "")}` — downstream services use `user["user_id"]` as `tenant_id`; no other payload fields needed at this stage.
- `CLERK_FRONTEND_API` env var drives the JWKS URL construction — no Clerk SDK dependency, just PyJWT + httpx.

**Gotchas:**
- `ruff` / `pyright` issues in `neo4j_adapter.py`, `presidio_adapter.py`, `metadoc_service.py`, `workers/main.py`, and `metadoc_tasks.py` were surfaced and fixed as part of the `make quality` gate — these were pre-existing lint debts exposed by the stricter import checks added for STORY-018.
- `cryptography>=43.0.0` is required by PyJWT for RS256 algorithm support — must be listed explicitly in `pyproject.toml` dependencies; PyJWT alone does not pull it in transitively on all platforms.

**Tech debt noted:**
- Webhook handler does not yet handle `user.deleted` events — user deactivation / cascade deletion is deferred to STORY-024 (GDPR).
- `require_user` does not enforce subscription tier or active account status — credit checks remain in `MetadocService`; a unified middleware guard should be added before Phase B.

---

## Sprint 14 — Credits System

> Credit ledger, deduction per operation, 402 enforcement.
> Sprint 14 covers STORY-023.

### STORY-023 — Credits System
**Date:** 2026-03-28 | **Sprint:** 14 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 211 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `3514980`

**What was built:**
`CreditService` with `deduct()` and `add_credits()` using SELECT FOR UPDATE for atomic credit mutations, `get_balance()`, and `get_recent_transactions()`. `GET /v1/credits/balance` returns balance + last 20 transactions. `POST /webhooks/stripe` handles `checkout.session.completed` to add credits via Stripe metadata. `user.created` webhook writes 500-credit signup bonus via `CreditService.add_credits()`. Ingestion tasks deduct 1 credit per page; meta-doc generation deducts 18 (Haiku) or 45 (Sonnet). Alembic migration added for `credits_balance` default constraint.

| Stat | Count |
|---|---|
| Files created | 4 |
| Files modified | 7 |
| Tests added | 15 |
| ACs complete | 6/6 |

**Key decisions:**
- Credit deduction in ingestion uses `continue` on `HTTPException(402)` — insufficient credits logs a warning but does not abort the ingestion job (non-blocking deduction per spec).
- Signup bonus applied after the initial `db.commit()` that creates the User — ensures the User row exists before `add_credits()` issues its SELECT FOR UPDATE.
- `CreditService` patched in `test_user_created_inserts_user` webhook test to avoid needing `db.exec` mocked with correct SELECT FOR UPDATE response shape.

**Gotchas:**
- `test_user_default_fields` expected `credits_balance == 200` — the model default is `0`; the 500-credit signup bonus is applied via CreditService, not as a model-level default. Test updated to expect `0`.
- `test_generate_meta_document_publishes_done_event` mock session needed `exec` mocked to return `MagicMock().one()` (not `AsyncMock`) because `db.exec(...)` returns a scalar result, not a coroutine.
- `test_user_created_inserts_user` webhook integration test needed `CreditService` patched since the mock DB's `exec` wasn't set up for SELECT FOR UPDATE; the test now asserts `add_credits` was called with the correct args.

**Tech debt noted:**
- Ingestion per-page credit deduction calls `CreditService.deduct()` inside the worker for each page individually — could be batched into a single deduction at the end of ingestion for efficiency.

---

## Sprint 15 — GDPR + PII Masking

> Full cascade deletion, Presidio entity consistency, 60s SLA.
> Sprint 15 covers STORY-024 and STORY-025.

### STORY-024 — GDPR Account Deletion Cascade
**Date:** 2026-03-28 | **Sprint:** 15 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean
**Commit:** `11c69f5`

**What was built:**
`DELETE /v1/account` endpoint returning 202 and enqueuing `cascade_delete_account` ARQ task. `DeletionService` orchestrates deletion across Storage → Qdrant → Neo4j → PostgreSQL → Clerk in that fixed order. Each step is individually try/excepted so partial failure never aborts the cascade (GDPR best-effort).

**Key decisions:**
- Deterministic `_job_id=f"gdpr:{user_id}"` on ARQ enqueue prevents duplicate deletion jobs from double-clicks; `enqueue_job` returns `None` on dedup so we fall back to the deterministic ID for the response.
- `require_user` called directly (not via `Depends`) in the route so `patch("src.api.routes.account.require_user")` works in tests — FastAPI captures `Depends` references at decoration time, making them unpatchable.
- PostgreSQL FK-safe order: job_statuses → credit_transactions → meta_documents → conflicts → source_authority_weights → sources → system_profiles → users. `chat_sessions`, `data_retention_logs`, and `referral_transactions` intentionally excluded (tables don't exist yet).
- Neo4j deletion uses two queries: one for all nodes with `tenant_id` (Memory, Concept, etc.) and a separate one for the `User` root node (which uses `user_id` not `tenant_id` per schema).
- `db.execute()` (not `db.exec()`) required for `TextClause` — pyright rejects `exec()` for raw SQL.

**Gotchas:**
- `QdrantAdapter.delete_by_filter` already existed and accepted `tenant_id=` kwarg — no changes needed to Qdrant adapter.
- `CLERK_SECRET_KEY` was already present in `config.py` as `str = ""` — plan step to add it was a no-op.

**Tech debt noted:**
- `DeletionService.delete_postgres_by_tenant` uses raw SQL strings (module-level constants) rather than ORM deletes — acceptable for GDPR one-shot but diverges from the ORM-first pattern elsewhere.

---

### STORY-025 — PII Masking in Production + Presidio Config
**Date:** 2026-03-28 | **Sprint:** 15 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 225 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `420fd59`

**What was built:**
`PresidioAdapter.mask_text(text, job_id, redis)` — async method with deterministic cross-chunk entity aliasing via Redis. Loads existing `pii:map:{job_id}` from Redis on each call so the same PII token in different chunks always receives the same `Entity_NNN` alias. Uses `presidio_analyzer.AnalyzerEngine` for detection (PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, US_SSN, LOCATION) and `presidio_anonymizer.AnonymizerEngine` with a `custom` operator (lambda closure over entity_map) for substitution. `setex` saves the updated map back to Redis with a 3600s TTL only after successful `anonymize` call. `generate_meta_document` worker (Phase 2) calls `mask_text` per chunk when `ENABLE_PII_MASKING=True`; a `finally` block deletes `pii:map:{job_id}` after the job completes or fails. Top-level `PresidioAdapter` import removed from `metadoc_tasks.py` (RULE 6 — lazy import inside the `if settings.ENABLE_PII_MASKING` branch). Pyright `arg-type` suppression added for `presidio_analyzer`/`presidio_anonymizer` `RecognizerResult` type mismatch (two packages export the same class under different module paths). `test_credits.py::test_metadoc_task_uses_credit_service_deduct` updated to remove stale module-level `PresidioAdapter` patch and set `mock_settings.ENABLE_PII_MASKING = False` to skip the PII branch.

| Stat | Count |
|---|---|
| Files created | 2 (presidio_adapter.py rewrite, test_presidio_adapter.py rewrite) |
| Files modified | 4 (metadoc_tasks.py, test_metadoc_tasks.py, test_credits.py) |
| Tests added | 7 |
| Total tests | 225 |

**Key decisions:**
- Entity map stored in Redis (not process memory) so cross-chunk consistency holds even if a future refactor parallelises chunk masking across worker processes.
- `OperatorConfig("custom", {"lambda": ...})` with a closure `m=entity_map` — avoids the late-binding problem where a plain `lambda x: entity_map[x]` would capture by reference and only see the final state of the map.
- `setex` called AFTER `anonymize`, not before — if anonymization raises, no stale partial map is persisted.
- `# type: ignore[arg-type]` on the `analyzer_results` kwarg — pyright correctly detects that `presidio_analyzer.RecognizerResult` and `presidio_anonymizer.entities.engine.recognizer_result.RecognizerResult` are nominally distinct despite being the same class at runtime.

**Gotchas:**
- `ruff format` reformatted the `# type: ignore[arg-type]` comment to a different line in the multi-line `anonymize(...)` call, causing the suppression to apply to the wrong argument. Fixed by re-running format and verifying the comment stayed on the `analyzer_results=results` line.
- `test_metadoc_task_uses_credit_service_deduct` in `test_credits.py` patched `src.workers.metadoc_tasks.PresidioAdapter` — a name that was removed by STORY-025's lazy-import refactor. Fixed by removing that patch line and explicitly setting `mock_settings.ENABLE_PII_MASKING = False` so the PII branch is skipped entirely in that test.

**Tech debt noted:**
- `mask_text` opens a Redis `get` + `setex` round-trip per chunk sequentially. For sources with many chunks this could be batched or the map cached in the adapter instance for the duration of one job.

---

## Sprint 16 — Chat Backend + Import Prompt

> Chat SSE streaming, multi-turn sessions, AI import helper endpoint.
> Sprint 16 covers STORY-026 and STORY-028-BE.

### STORY-026 — Conversational Memory Chat (Backend)
**Date:** 2026-03-29 | **Sprint:** 16 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 247 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `63d1b2d`

**What was built:**
Direct-SSE conversational chat over the user's memory base. `POST /v1/chat/message` streams Anthropic tokens via `EventSourceResponse` with session auto-creation, 6-message history window, Qdrant+Neo4j hybrid retrieval (RAGService reused from STORY-015), credit deduction only after a successful full response, and bleach sanitization on the assistant response. `GET /v1/chat/sessions` (paginated), `GET /v1/chat/sessions/{id}`, and `DELETE /v1/chat/sessions/{id}` manage session lifecycle. Alembic migration creates `chat_sessions` table with JSONB messages column and composite DESC index.

**Key decisions:**
- `stream_turn()` is an async generator on `ChatService` (not inline in the route) — route stays thin, all business logic in the service layer.
- `AnthropicAdapter.stream_completion()` used instead of `AsyncAnthropic()` directly — satisfies RULE 1 three-layer boundary and uses `settings.ANTHROPIC_API_KEY` correctly. TODO comment added for future `LLMRouter.stream()` migration.
- `RAGService` and `AnthropicAdapter` both lazily imported inside `stream_turn()` body per RULE 6; `RAGService` wrapped in `try/finally` for `cleanup()`.
- Credit check uses `user_obj.credits_balance` (fetched for tier check anyway) before streaming; `CreditService.deduct()` runs only after `full_response` fully accumulated — no charge on timeout or LLM error.
- `user_id` on `ChatSession` is `str` (not `uuid.UUID`) — Clerk string IDs per STORY-018-BE change.
- `str(c.source_id)` replaces non-existent `source_filename` field in citations and system prompt.
- JSONB used for `messages` column (matching `meta_document.py` convention) rather than generic JSON.

**Gotchas:**
- `patch("src.services.rag_service.RAGService")` is the correct patch target (definition site) because `RAGService` is lazily imported inside `stream_turn()` and never in the `chat_service` module namespace.
- `CreditService.deduct()` calls `db.exec()` with `with_for_update()` internally — the SSE streaming test needed `CreditService.deduct` patched to avoid exhausting the mock DB's `exec` side_effect list (configured only for `get_sessions`'s two-call pattern).
- `func.count(ChatSession.id)` in `get_sessions()` required `# type: ignore[arg-type]` — pyright doesn't recognize SQLModel field descriptors as `_ColumnExpressionArgument`.
- Import order in `test_chat_service.py` needed ruff I001 fix (stdlib → first-party order).

**Tech debt noted:**
- `AnthropicAdapter` called directly rather than via `LLMRouter` — LLMRouter has no streaming interface yet. TODO(STORY-028+) comment in place.
- `stream_turn()` creates fresh `RAGService()` per request — if adapters hold connection pools, a constructor-injection pattern would be cleaner for lifecycle management.

---

### STORY-028-BE — AI Chat Context Import Helper (Backend)
**Date:** 2026-03-29 | **Sprint:** 16 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 251 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `0d34aa7`

**What was built:**
`GET /v1/ingest/import-prompt` endpoint that reads user's Concept nodes from Neo4j (scoped by tenant_id + optional profile_id) and returns a personalized extraction prompt with detected concept labels. New users with no Concept nodes receive a generic fallback prompt — no 404 is raised. New schema `ImportPromptResponse(prompt_text, detected_concepts)`, new `IngestionService.generate_import_prompt()` method, and new `Neo4jAdapter.get_concepts_for_tenant()` adapter method added.

| Stat | Count |
|---|---|
| Routes added | 1 (`GET /v1/ingest/import-prompt`) |
| Service methods added | 1 (`IngestionService.generate_import_prompt`) |
| Adapter methods added | 1 (`Neo4jAdapter.get_concepts_for_tenant`) |
| Schemas added | 1 (`ImportPromptResponse`) |
| Tests added | 4 (integration) |

**Key decisions:**
- Fallback to generic prompt (not 404) when user has no Concept nodes — new users should still receive a usable response on first import.
- `profile_id` is an optional query parameter; when omitted the query returns all Concept nodes for the tenant without profile scoping.
- tenant_id passed as Neo4j query parameter per RULE 11 — never string-interpolated into Cypher.

**Gotchas:**
- `ruff format` reformatted the test file import block, requiring a separate fix commit to pass the pre-commit I001 check.

**Tech debt noted:**
- None.

---

## Sprint 17 — Natural Language Graph Query

> Text-to-Cypher backend endpoint.
> Sprint 17 covers STORY-029.

### STORY-029 — Natural Language Graph Query (Backend)
**Date:** 2026-03-29 | **Sprint:** 17 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 283 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `b8c018f`

**What was built:**
`POST /v1/graph/query` endpoint that converts natural language to Cypher via `LLMRouter("cypher_generation")` (Gemini 2.5 Flash primary, Claude Haiku fallback). Generated Cypher is checked against a write-keyword regex before execution. Tenant filter injected as a Cypher `$tenant_id` parameter reference (never string-interpolated). Results parsed with the existing `GraphService._rows_to_graph_response()` helper and returned as `{cypher, results: {nodes, edges}, explanation, query_time_ms}`. Credit cost: 2 per query via `CreditService.deduct()` before LLM call.

| Stat | Count |
|---|---|
| Routes added | 1 (`POST /v1/graph/query`) |
| Services added | 1 (`GraphQueryService`) |
| Schemas added | 2 (`GraphQueryRequest`, `GraphQueryResponse`) |
| Error codes added | 1 (`UNSAFE_QUERY`) |
| Tests added | 30 (unit + integration) |

**Key decisions:**
- `response_format` intentionally omitted from `LLMRouter.complete()` — Cypher is plain text, not JSON. The story spec incorrectly included `response_format={"type": "json_object"}`.
- `inject_tenant_filter` injects `$tenant_id` (Cypher parameter placeholder), not the literal value. The actual value travels via `run_query(..., tenant_id=tenant_id)` per RULE 11.
- User query wrapped in `<user_query>` XML tags in the prompt per RULE 10.
- Reuses `GraphService._rows_to_graph_response()` by mandating a canonical RETURN clause format (`n_type, n_props, r_type, r_props, m_type, m_props`) in the LLM prompt — avoids duplicating node/edge parsing.
- Credits deducted before LLM call (fail fast on 0-credit users); no refund on LLM or Neo4j failure.

**Gotchas:**
- `BaseService.__enter__`/`__exit__` are defined but no service in this codebase uses `with Service() as svc:` syntax in routes — use plain instantiation instead.
- The story spec's `inject_tenant_filter` had a RULE 11 violation (string-interpolated literal `tenant_id`); corrected to inject `$tenant_id` parameter reference.

**Tech debt noted:**
- Credits are not refunded if the LLM or Neo4j call fails after deduction. A retry/refund mechanism is out of scope.

---

## ✅ Backend Gate Checkpoint

_This section is filled in when all 17 backend sprints are complete._

**Date passed:** _not yet_
**`make test` result:** _not yet_
**`make quality` result:** _not yet_
**`npm run generate-client` result:** _not yet_

---

## Sprint 18 — Admin Dashboard Backend

> Admin API: user management, credit adjustment, platform stats.
> Sprint 18 covers STORY-036-BE.

### STORY-036-BE — Admin API Endpoints (Backend)
**Date:** 2026-03-29 | **Sprint:** 18 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 302 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `c711916`

**What was built:**
`require_admin` FastAPI dependency (checks `ADMIN_USER_IDS` env var, returns 403 for non-admins) + 5 admin-only REST endpoints: `GET /v1/admin/users` (paginated list + email search), `GET /v1/admin/users/{user_id}` (user detail with last-20 credit transactions + source count), `POST /v1/admin/credits/adjust` (signed amount, produces `CreditTransaction(operation="admin_adjustment")` audit trail, allows negative balance), `POST /v1/admin/users/{user_id}/toggle-active` (ban/unban), `GET /v1/admin/stats` (platform metrics including Redis `llm:daily_spend:{today}` key read via arq_pool).

| Stat | Count |
|---|---|
| Routes added | 5 (`/v1/admin/users`, `/v1/admin/users/{id}`, `/v1/admin/credits/adjust`, `/v1/admin/users/{id}/toggle-active`, `/v1/admin/stats`) |
| Services added | 1 (`AdminService`) |
| Dependencies added | 1 (`require_admin`, `get_arq_pool` in `src/api/dependencies/admin.py`) |
| Schemas added | 8 (in `src/schemas/admin.py`) |
| Tests added | 19 (integration, all mocked) |

**Key decisions:**
- `require_admin` wraps `require_user` via `Depends(require_user)` — never bypasses JWT validation.
- Stats route pre-fetches Redis spend as `float` before calling `AdminService.get_stats()` — keeps service layer Redis-free.
- Admin credit adjustments bypass the balance guard in `CreditService.deduct()` — intentional, admin CAN produce negative balances.
- `Source.ingested_at` and `MetaDocument.generated_at` used for "today" counts (not `created_at`).

**Gotchas:**
- `raise_404` did not exist in errors.py — added before AdminService was implemented (same pattern as raise_402, raise_403, raise_409).
- `test_list_users_without_auth_returns_401` used an undefined `client` fixture — replaced with inline AsyncClient pattern matching the rest of the integration tests.
- `func.count(Source.id)` in `get_user_detail` required `# type: ignore[arg-type]` — same pyright issue seen in chat_service.py and graph_query_service.py.

**Tech debt noted:**
- Admin credit adjustments bypass CreditService.deduct() entirely — inline SELECT FOR UPDATE in AdminService.adjust_credits(). If CreditService gains new side effects (e.g. notifications), admin adjustments won't inherit them automatically.
- GET /v1/admin/stats runs 6 separate COUNT queries sequentially. Could be parallelised with asyncio.gather() for sub-100ms latency.

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

## Sprint 34 — Admin Dashboard

> Frontend: admin UI with user management, credit adjustment, and stats dashboard.
> Sprint 34 covers STORY-036-FE.

_No entries yet._

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
