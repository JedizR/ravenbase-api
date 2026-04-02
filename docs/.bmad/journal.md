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
| Total stories complete | 41 / 43 |
| Current phase | Phase B — Production Launch (EPIC-10) |
| Current sprint | 41 |
| Active repo | ravenbase-web + ravenbase-api |
| Project started | 2026-03-25 |
| Last entry | 2026-04-02 (STORY-041: Sources page upload wired, deployment config files created, UX gaps closed) |

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

## Sprint 21 — Onboarding + Profile Switching

> 3-step wizard, GettingStartedChecklist, profile context.
> Sprint 21 covers STORY-019 and STORY-020.

### STORY-019 — Onboarding Wizard
**Date:** 2026-03-30 | **Sprint:** 21 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 7 tests passing, 0 TypeScript errors
**Commit:** `00dde32`

**What was built:**
3-step onboarding wizard at `/onboarding`: Step 1 (role grid + auto-filled profile name with blur-debounce validation), Step 2 (IngestionDropzone + textarea paste with file/text upload), Step 3 (SSE progress bar via `useSSE` hook with auto-advance to `/dashboard?first_run=true`). Register page now redirects new users to `/onboarding` instead of `/dashboard`. Completion calls `POST /v1/users/me/complete-onboarding` (graceful error if backend not yet deployed). Returning users who already completed onboarding are redirected to `/dashboard` via `GET /v1/users/me` check on mount.

**Key decisions:**
- `useSSE` hook uses `?token=` query param (not Authorization header) — EventSource is browser-native and cannot set custom headers; backend reads token via `verify_token_query_param` dependency.
- `completeOnboarding()` is best-effort (try/catch swallows backend errors) — wizard always navigates to dashboard regardless of API availability, so onboarding UX works even before backend `POST /v1/users/me/complete-onboarding` is deployed.
- Role grid pre-fills profile name via `ROLE_DEFAULTS` map but only if the user hasn't manually touched the field (`profileNameTouched` guard) — avoids overwriting intentional edits.
- Text ingestion uses `{ content: pastedText }` body field (not `{ text }`) per TextIngestRequest schema from STORY-008-BE.
- SSE endpoint path: `/v1/ingest/stream/{source_id}` — upload response returns `source_id`, not `job_id`.
- `Providers` (QueryClientProvider) wraps the wizard in `page.tsx` — onboarding is under `(auth)/` which has no provider by default.

**Gotchas:**
- `useRef<ReturnType<typeof setTimeout>>()` is invalid in strict TypeScript (requires initial argument) — must use `useRef<ReturnType<typeof setTimeout> | undefined>(undefined)`.
- Tailwind v4 canonical class for `min-height: 100dvh` is `min-h-dvh` (not `min-h-[100dvh]`) — IDE lint flagged the arbitrary value.

**Tech debt noted:**
- AC-7 (skip onboarding for returning users) depends on `GET /v1/users/me` returning `has_completed_onboarding` — backend User model needs the field added plus Alembic migration (ravenbase-api scope). Frontend guard is wired but silently fails if endpoint returns 404.
- Backend `POST /v1/users/me/complete-onboarding` endpoint not yet deployed — onboarding flag is not persisted until ravenbase-api adds this route.

---

### STORY-020 — System Profile Switching
**Date:** 2026-03-30 | **Sprint:** 21 | **Phase:** B | **Repo:** ravenbase-web + ravenbase-api
**Quality gate:** ✅ clean — 333 backend tests passing, 0 TypeScript errors
**Commit:** `d3e4fee`

**What was built:**
Backend: `GET/POST/PATCH/DELETE /v1/profiles` CRUD endpoints (`src/api/routes/profiles.py`), `PATCH /v1/account/model-preference` and `PATCH /v1/account/notification-preferences` (`src/api/routes/account.py`), `ProfileResponse`/`ProfileCreate`/`ProfileUpdate` Pydantic schemas (`src/schemas/profile.py`). Frontend: `ProfileContext` (pure client state, no API call on switch), `ProfileSwitcher` (shadcn DropdownMenu with color badge), `Sidebar` (forest green, desktop), `MobileSidebar` (shadcn Sheet, mobile), `Omnibar` (cmdk Command with `/profile` fuzzy match), `DashboardHeader`, Settings → Profiles CRUD page, Settings → AI Model + Notification toggles. Build: 0 TypeScript errors, all routes rendered in `next build`.

**Key decisions:**
- Profile switching is pure client `setActiveProfile()` — no API call, instant (< 50ms) per AC-4.
- `ProfileContext` fetches `GET /v1/profiles` once on mount and caches in React state; CRUD helpers (`createProfile`, `updateProfile`, `deleteProfile`) live in context for easy access.
- Omnibar `/profile [name]` uses cmdk Command component (shadcn `CommandInput`/`CommandList`/`CommandGroup`), fuzzy matches via simple character-in-order check against all profile names.
- `useRef<ReturnType<typeof setTimeout> | undefined>(undefined)` pattern used in all hooks — `useRef<T>()` without initial value is invalid in strict TypeScript.
- `PATCH /v1/profiles/{id}` uses `exclude_unset=True` for partial updates; setting `is_default=True` unsets other defaults in a separate query first.
- Settings page uses `useApiFetch` (client hook) not `apiFetch` (server-only) — `apiFetch` from `@/lib/api` cannot be imported in `"use client"` components (contains `@clerk/nextjs/server`).
- `db.add()` and `db.add_all()` are synchronous in SQLModel async session — no `await` prefix (pyright caught this).

**Gotchas:**
- `await db.add()` and `await db.add_all()` are wrong — `db.add()` is synchronous in SQLModel async sessions. Correct: `db.add(profile)` without `await` (pyright error: "None is not awaitable").
- `apiFetch` from `@/lib/api` contains `import 'server-only'` making it server-only — client components MUST use `useApiFetch` from `@/lib/api-client`.
- Omnibar is rendered in the header area with `position: absolute; bottom-full` so it pops up above the input — works on both mobile and desktop layouts.

**Tech debt noted:**
- `GET /v1/users/me` endpoint not in OpenAPI spec — Settings page falls back to defaults if the call fails. Backend should add this endpoint (or wire existing `POST /v1/users/me/complete-onboarding` as GET too).
- No cross-profile search toggle (AC-6) implemented yet — Omnibar `/search` command is a nav stub; full cross-profile search is deferred to a future story.
- Credits balance in sidebar footer is a static `— —` placeholder — wire up via `GET /v1/credits/balance` in a future story.

---

## Sprint 25 — AI Chat Import UI

> Import helper tab on Sources page.
> Sprint 25 covers STORY-028-FE.

### STORY-028-FE — AI Chat Import Helper UI
**Date:** 2026-03-30 | **Sprint:** 25 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 5 tests passing, 0 TypeScript errors
**Commit:** `2add09a`

**What was built:**
Sources page at `/sources` with two tabs (Upload Files + Import from AI Chat). Import tab has: profile selector (shadcn Select), personalized extraction prompt loaded from GET /v1/ingest/import-prompt via TanStack Query (falls back to generic prompt on error), GeneratedPromptBox with one-click Clipboard API copy + 2-second "Copied" feedback, collapsible numbered instructions on mobile, paste-back textarea (100k char limit, char counter), Import button calling POST /v1/ingest/text with SSE-driven IngestionProgress replacing the button on submit. State machine: idle → pending → streaming → complete → idle.

**Key decisions:**
- Used `vi.hoisted()` for mock functions in tests — required because vitest hoists `vi.mock()` calls before module evaluation, making `mockGetImportPrompt` unavailable to the factory without hoisting.
- `id="profile-select"` placed on `SelectTrigger` (not `Select` root) since shadcn Select doesn't forward `id` to its root element.
- Mobile instructions use manual `hidden md:block` toggle via `useState` instead of shadcn `Collapsible` — avoids adding a new shadcn dependency.
- Import button is `disabled={!pastedText.trim()}` when idle (prevents empty submit) rather than allowing click with toast error.

**Gotchas:**
- `vitest` in this project doesn't have `@testing-library/jest-dom` installed — all assertions use vanilla vitest Chai API: `toHaveProperty()` instead of `toHaveValue()`, `toBeTruthy()` instead of `toBeInTheDocument()`, `hasAttribute("disabled")` instead of `toBeDisabled()`.
- The `Select` component from shadcn doesn't forward `id` to its root — resolved by placing `id` on `SelectTrigger` child instead.
- `toast.error` not called when Import clicked with empty textarea because button is disabled — test 4 verifies disabled state instead of error toast.

**Tech debt noted:**
- GeneratedPromptBox has no error state — always shows the provided promptText. If promptText is empty string, textarea shows empty content.

---

## Sprint 22 — SSE Progress + Omnibar UI

> IngestionProgress SSE component, text quick-capture Omnibar UI.
> Sprint 22 covers STORY-007-FE and STORY-008-FE.

### STORY-007-FE — IngestionProgress Component
**Date:** 2026-03-30 | **Sprint:** 22 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 7 tests passing, 0 TypeScript errors
**Commit:** `8d767cb`

**What was built:**
`hooks/use-sse.ts` updated to accept `progress_pct` fallback alongside `progress` (backend sends `progress_pct` field name). `components/domain/IngestionProgress.tsx` created with real-time SSE progress bar using the existing `useSSE` hook, shadcn `Progress` + `Skeleton`, complete/error/connecting states, `aria-live="polite"` region, and `CheckCircle2`/`XCircle` lucide icons for terminal states.

**Key decisions:**
- Token fetched via `useAuth().getToken()` (Clerk frontend SDK) and passed to `useSSE` as query param — same pattern as `OnboardingWizard`.
- `useSSE` hook handles `EventSource` lifecycle (mount → connect → message → cleanup) and auto-closes on `completed`/`failed` status.
- Progress bar uses default `bg-primary` (forest green) for `processing` state; overridden to `bg-success` or `bg-destructive` for terminal states via `[&_[data-slot=progress-indicator]]` selector.

**Gotchas:**
- The `useSSE` hook's `SSEState` type expected `progress` field but backend SSE sends `progress_pct`. Added `data.progress_pct ?? prev.progress` fallback to fix field name mismatch at the hook level.

**Tech debt noted:**
- `IngestionProgress` is standalone; not yet wired into `IngestionDropzone` or the onboarding wizard — will be integrated in a future story.

---

### STORY-008-FE — Omnibar /ingest Command
**Date:** 2026-03-30 | **Sprint:** 22 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 13 tests passing, 0 TypeScript errors
**Commit:** `0588f06`

**What was built:**
`/ingest` command added to `components/domain/Omnibar.tsx`. Typing `/ingest [text]` + Enter calls `useApiFetch` → POST /v1/ingest/text with `{ content, profile_id, tags }`. Shows `toast.success("Captured to [ProfileName]")` on success. `/search` and `/generate` show `toast.info("Command not yet implemented")` instead of navigating.

**Key decisions:**
- Used `useApiFetch` from `lib/api-client.ts` (not the generated `ingestTextV1IngestTextPost` from services.gen.ts) — follows CLAUDE.md RULE 3 pattern.
- Enter keydown handled via `onKeyDown` on `CommandInput` — no `<form>` tag (RULE 1).

**Gotchas:**
- Component testing required two additional dev dependencies:
  `@vitejs/plugin-react` v4 (for vitest JSX transformation) and
  `@testing-library/dom` — neither was in the original scaffold.
  Without these, vitest cannot render React components.
- Stale `.next` cache caused 404s on layout.css and main-app.js
  after STORY-007-FE changes. Fixed by clearing cache with
  `rm -rf .next` before starting dev server.

**Tech debt noted:**
- `/search` and `/generate` commands are stubbed with
  "not yet implemented" toasts. Full implementations are
  deferred: /search to the NL graph query story (STORY-030),
  /generate to the Workstation story (STORY-017).
- Credits balance in sidebar footer is still static "— —" —
  deferred to a future story wiring GET /v1/credits/balance.

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

## Sprint 23 — Workstation UI

> Streaming Markdown, export, auto-save ◆ status indicator.
> Sprint 23 covers STORY-017.

### STORY-017 — Workstation UI (SSE Streaming + Markdown + Export)
**Date:** 2026-03-30 | **Sprint:** 23 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 13 tests passing, 0 TypeScript errors
**Commit:** `747c30b`

**What was built:**
Workstation page at `/workstation` with two-panel layout (history sidebar + editor). MetaDocEditor streams SSE tokens and renders Markdown progressively via `react-markdown` (dynamic import, SSR disabled). Auto-save status indicator per RULE 19 (`◆ GENERATING` / `◆ SAVED_JUST_NOW` / `◆ SAVED_2_MIN_AGO`). Export to .md via Blob anchor download, export to PDF via `window.print()` with `@media print` CSS. Mobile collapses history into a shadcn Sheet. `useSSEStream` hook created as separate from existing `useSSE` (ingestion) for token accumulation.

**Key decisions:**
- `use-sse-stream.ts` created as a new hook separate from `use-sse.ts` (which handles ingestion progress with `progress_pct/message` fields). New hook accumulates `type: "token"` events into a string.
- `react-markdown` uses `dynamic(() => import("react-markdown"), { ssr: false })` per CLAUDE.md performance rules — heavy component must not be in initial bundle.
- Backend `GET /v1/metadoc` endpoint added to ravenbase-api before frontend work (Phase 0) since STORY-016 only created `POST /generate` and `GET /stream/{job_id}`.
- No `<form>` tags in prompt area — uses div + controlled Textarea + onClick button per CLAUDE.md RULE 1.
- `remark-gfm` imported normally (plugin object, not heavy component).

**Gotchas:**
- `MetaDocSummary` in generated client uses camelCase `pageSize` not snake_case `page_size` — fixed in `MetaDocHistory.tsx`.
- `initialDocId` prop typed as `?: string` but defaulted to `null` — TypeScript error. Fixed by changing type to `?: string | null`.
- `remarkGfm` import was missing from MetaDocEditor — added `import remarkGfm from "remark-gfm"` after the services import.

**Tech debt noted:**
- `MetaDocDetail` endpoint (`GET /v1/metadoc/{doc_id}`) not implemented in backend — history panel currently loads documents from localStorage or shows prompt only. Future story should add this endpoint to enable full doc reload from server.
- Sources panel shows "Generate a document to see which memory nodes contributed" — contributing memory count not yet wired up (would require `MetaDocDetail` endpoint).

---

## Sprint 30 — Pricing Page + Stripe Checkout

> Public pricing page, Stripe Checkout session, Redis-idempotent webhook tier upgrade.
> Sprint 30 covers STORY-022.

### STORY-022 — Pricing Page + Stripe Checkout
**Date:** 2026-03-31 | **Sprint:** 30 | **Phase:** B | **Repo:** ravenbase-web + ravenbase-api
**Quality gate:** ✅ clean — backend: make quality + make test passing; frontend: 0 TypeScript errors, build passes
**Commit:** `4f606bf`

**What was built:**
Public `/pricing` page (Server Component, SSG) with Free/Pro/Team tier cards, monthly/annual billing toggle, and feature comparison table. Stripe Checkout sessions created server-side via `POST /v1/billing/create-checkout-session`; the frontend never touches Stripe directly. Backend webhook handler upgraded with Redis idempotency (`stripe:event:{event_id}`, 24h TTL), tier upgrade routing via `session_type` metadata, and `customer.subscription.deleted` → revert tier to free. Settings → Billing page at `/settings/billing` with Stripe Customer Portal link. Checkout success toast shown via `CheckoutSuccessHandler` on redirect back to `/chat?checkout=success`.

**Key decisions:**
- Distinguished tier upgrades from credit top-ups using `session_type` metadata in the Checkout session — avoids breaking changes to existing credit top-up flow which routes on the same `checkout.session.completed` event type.
- `stripe.api_key` set at module level in `billing_service.py`, not in `__init__` — prevents invisible coupling where webhooks would fail if BillingService was never instantiated.
- Used `with_for_update()` on the Stripe customer lookup to prevent TOCTOU race that would create duplicate Stripe customers under concurrent requests.
- `handled = False` flag in webhook handler ensures `redis.setex` is only called when an event type is actually processed — prevents permanent suppression of unknown event types.
- `(dashboard)` route group does NOT add a `/dashboard/` URL segment — success_url points to `/chat?checkout=success`, return_url to `/settings/billing`.
- Alembic migration for `stripe_customer_id` created manually (not autogenerate) — autogenerate picked up unrelated model diffs and produced destructive DROP TABLE operations.
- Added `index=True` to `stripe_customer_id` field after code quality review because `_handle_subscription_deleted` queries users by this column.
- Marketing layout added `QueryClientProvider` wrapping — `PricingSection` uses `useQuery` which requires a QueryClient; the layout previously had none, causing a "No QueryClient set" build failure.

**Gotchas:**
- Alembic `--autogenerate` was attempted first and produced a migration with DROP TABLE for unrelated tables (`chat_sessions`, `data_retention_logs`) — had to roll back, delete the bad file, and write the migration manually.
- Hardcoded Postgres credentials were added to `alembic/env.py` during a bad implementer run — reverted via `git restore` to use `settings.DATABASE_URL`.
- Stripe SDK async methods: `stripe.Customer.create_async()` not `stripe.Customer.create()` — synchronous variants block the event loop in async FastAPI routes.
- `useSearchParams()` in Next.js 15 requires a `<Suspense>` boundary in the parent layout — without it `npm run build` fails with a missing Suspense boundary error.

**Tech debt noted:**
- None introduced.

---

## Sprint 26 — Graph Explorer UI

> Cytoscape.js force-directed graph, node detail panel, mobile degradation.
> Sprint 26 covers STORY-011.

### STORY-011 — Graph Explorer UI (Cytoscape.js)
**Date:** 2026-03-31 | **Sprint:** 26 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 47 tests passing, 0 TypeScript errors
**Commit:** `0373e4a`

**What was built:**
Force-directed knowledge graph visualization using Cytoscape.js with cytoscape-fcose layout. Node types: concept (primary green #2d4a3e), memory (secondary #e8ebe6), source (accent #a8c4b2), conflict (amber #ffc00d with animate-pulse). Click-to-inspect node details with 2-hop neighborhood subgraph via GET /v1/graph/neighborhood/{node_id}. GraphFilters: profile selector, date range inputs, node type checkboxes (no form tags per CLAUDE.md RULE 1). Mobile fallback: ConceptList with search and type tabs for screens < 768px. Empty states: processing animation with pulsing logo, no sources empty state with upload CTA, no matching nodes with clear filters. GraphNodePanel: right-side Sheet with node details, type badge, connected nodes list, conflict warning card with "View in Inbox" button.

**Key decisions:**
- Cytoscape instance stored in useRef, not React state — prevents infinite re-render loop
- cytoscape and cytoscape-fcose dynamically imported inside useEffect — keeps heavy libs out of initial bundle
- GraphExplorer wrapped in next/dynamic with ssr:false — no SSR for browser-only Cytoscape
- Client components use useApiFetch() from lib/api-client.ts, not server-only apiFetch()
- ProfileContext passed as props to avoid context issues in dynamically imported components

**Gotchas:**
- @types/cytoscape NOT installed — Cytoscape v3.30 ships its own TypeScript types; installing @types/cytoscape separately causes duplicate declaration errors
- Tailwind v4 has no tailwind.config.js — graph container height set via className on the div ref container

**Tech debt noted:**
- Conflict node CSS pulse animation not yet working via Cytoscape stylesheet — needs DOM overlay approach or custom Cytoscape extension

---

## Sprint 29 — Landing Page

> Full marketing landing page with 9 sections and animations.
> Sprint 29 covers STORY-021.

### STORY-021 — Landing Page (Hero + Features + Workflow + CTA)
**Date:** 2026-03-31 | **Sprint:** 29 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 78 tests passing, 0 TypeScript errors, build passes
**Commit:** `4d88549`

**What was built:**
Full 9-section marketing landing page at app/(marketing)/page.tsx, replacing the old root redirect (app/page.tsx deleted). Components: Header (sticky scroll + mobile hamburger), HeroSection (Framer Motion entrance animations + AnimatedGraph.tsx SVG with 24 nodes/36 edges), WorkflowSection (3-step Upload→Structure→Generate cards, anchor id="how-it-works"), FeaturesSection (staggered whileInView scroll animations on 3 feature cards), FeatureDeepDive (alternating layout with Memory Inbox and Meta-Document styled mockups), TestimonialsSection (3 REF-XXXX placeholder cards), FAQSection (shadcn Accordion using radix-ui import pattern, 4 Q&As), CTASection (decorative corner icons, single CTA), Footer (mono status bar, legal + product nav). JSON-LD SoftwareApplication schema injected via next/script. robots.ts, sitemap.ts, and middleware.ts updated for marketing/dashboard route split.

**Key decisions:**
- Used Framer Motion `useInView` + `variants` for scroll-triggered animations rather than CSS-only to match the animation spec
- AnimatedSVG graph preview uses hardcoded demo nodes/edges — no real API call on the marketing page
- JSON-LD injected via Next.js `<Script>` with `dangerouslySetInnerHTML` per Google's recommended pattern (structured data, not rendered HTML)
- Middleware updated to allow unauthenticated access to all `(marketing)` routes while protecting `(dashboard)` routes

**Gotchas:**
- `framer-motion` requires `"use client"` on any component that uses motion hooks — marketing page is a Client Component as a result
- shadcn Accordion needed: `npx shadcn@latest add accordion --yes`

**Tech debt noted:**
- Testimonials section uses placeholder copy — real testimonials needed before launch
- GraphPreview SVG is static demo — could be replaced with a live read-only Cytoscape embed in a future polish story

---

## Sprint 28 — Natural Language Graph Query UI

> NL query bar, amber node highlights, results panel.
> Sprint 28 covers STORY-030.

### STORY-030 — Natural Language Graph Query Frontend
**Date:** 2026-03-31 | **Sprint:** 28 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 78 tests passing, 0 TypeScript errors
**Commit:** `06e85d1`

**What was built:**
GraphQueryBar component above the filter bar with example query chips (clicking fills input without submitting). POST /v1/graph/query via useApiFetch with {query, profile_id, limit:20}. GraphExplorer adds .query-match class to matched nodes with amber highlight (#ffc00d bg, #d97706 border, z-index 999) via Cytoscape. GraphQueryResults panel slides in from right with memory cards (content preview first 150 chars, source_name, confidence badge), collapsible "Show Cypher" section, empty state for zero results.

**Key decisions:**
- Example chips: clicking sets input value only, does NOT submit (per spec AC-7)
- GraphExplorer tap handler checks onResultCardClick prop: if provided uses it (query mode), else falls back to onNodeSelect (explore mode)
- GraphQueryResults only renders on desktop (isMobile check in GraphPageClient)
- Import path is `@/src/lib/api-client/types.gen` (NOT `@/lib/...`) — the Next.js `src/` directory means the alias starts with `@/src/`, so all imports from within `src/lib/api-client/` use the `src/` prefix

**Gotchas:**
- Original plan had wrong import path (@/lib/api-client) — corrected to @/src/lib/api-client
- toHaveValue/toBeDisabled are Jest-dom matchers not available in vitest — used .value property checks and .disabled attribute instead
- shadcn Collapsible component needed: ran npx shadcn@latest add collapsible --yes

**Tech debt noted:**
- GraphQueryResults panel does not have a close button — user must clear the query to dismiss
- Confidence badge only shown when confidence property exists on node

---

## Sprint 27 — Dark Mode + Email + Legal

> Theme toggle, transactional email, Privacy/Terms pages.
> Sprint 27 covers STORY-031, STORY-032, and STORY-033.

### STORY-031 — Dark Mode Toggle
**Date:** 2026-04-01 | **Sprint:** 27 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 0 TypeScript errors, build passes
**Commit:** `bd3e8f2`

**What was built:**
Dark/light mode toggle with `.dark` class on `<html>`, localStorage persistence via `ravenbase-theme` key, and no-flash blocking script in `<head>`. ThemeToggle button in dashboard header with Moon (light mode) / Sun (dark mode) icons and 44px touch target. Marketing pages respect stored preference. Smooth CSS transitions via `.transitioning` class.

**Key decisions:**
- Implemented per spec — no deviations
- `useTheme` hook: `useState(false)` (light default), `useEffect` with empty deps applies class before paint
- No-flash script uses `dangerouslySetInnerHTML` (only way to inject blocking inline scripts in Next.js App Router)
- `STORAGE_KEY = "ravenbase-theme"` matches both the hook and the blocking script
- Icon rotation: 180deg `transition-transform duration-300` on toggle

**Gotchas:**
- None encountered — straightforward implementation per spec

**Tech debt noted:**
- None.

---

## Sprint 27 — Memory Inbox UI

> Keyboard-driven triage, 3 flows (binary, conversational, auto-resolved).
> Sprint 27 covers STORY-014.

### STORY-014 — Memory Inbox UI (Keyboard Navigation + 3 Flows)
**Date:** 2026-03-31 | **Sprint:** 27 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 66 tests passing, 0 TypeScript errors
**Commit:** `93709c8`

**What was built:**
Keyboard-navigable conflict resolution interface with 3 flows: Binary Triage (J/K navigate cards, Enter accepts new, Backspace keeps old), Conversational (C opens chat mode, Enter submits custom resolution via CUSTOM action), Auto-resolved (TanStack Query optimistic updates with rollback on error). ShortcutOverlay modal triggered by ? key lists all keyboard shortcuts. Sidebar badge polls GET /v1/conflicts?status=pending every 30s. InboxEmptyState with animated SVG checkmark shown when all conflicts resolved. Sonner Toaster added to dashboard layout for rich toast notifications.

**Key decisions:**
- useKeyboardInbox hook uses window-level addEventListener (not element onKeyDown) — fires even when no card is focused
- Ignores keyboard events when e.target is HTMLInputElement or HTMLTextAreaElement via instanceof checks
- ConflictCard active state: border-2 border-primary; inactive: border border-border opacity-70
- TanStack Query onMutate pattern: cancelQueries → snapshot previous → setQueryData (optimistic remove) → return context; onError rolls back via context.previous; onSettled invalidates
- No `<form>` tags anywhere — ConflictChat uses div + controlled Textarea + onClick button per RULE 1
- Mobile swipe via onTouchStart startX/endX delta detection (progressive enhancement)
- Kbd component from shadcn (added via npx shadcn@latest add kbd --yes)

**Gotchas:**
- Tests require `// @vitest-environment happy-dom` at top of every test file — without it, "document is not defined"
- happy-dom doesn't set e.target on window KeyboardEvent — used Object.defineProperty(event, "target", { value: textarea }) to mock it in input-ignoring tests
- TanStack Query waitFor timeout issues in tests — replaced with `await new Promise(r => setTimeout(r, 100))` pattern for reliable async checking
- Conflict card assertion looked for "MEMORY_INFLICT" but actual text was "MEMORY_CONFLICT" — typo in test fixed

**Tech debt noted:**
- Conflict card pulse animation on conflict nodes not yet implemented (deferred from STORY-011)
- Credits balance in sidebar footer still static "— —" placeholder — not wired up in this story

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

## Sprint 32 — Transactional Email

### STORY-032 — Transactional Email via Resend
**Date:** 2026-04-02 | **Sprint:** 32 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 350 tests passing, 0 ruff errors, 0 pyright errors, 0 TypeScript errors
**Commit:** `0615cff`

**What was built:**
Backend: `EmailService` with `send_welcome`, `send_low_credits`, `send_ingestion_complete` methods using Resend API and brand-styled HTML email templates. API endpoints: `GET /v1/account/notification-preferences`, `POST /v1/account/notification-prefs/test/{type}` in account.py; `get_notification_preferences()` in `UserSettingsService`. Also added `GET /v1/metadoc` endpoint to fix pre-existing frontend error in `MetaDocHistory.tsx`. Frontend: dedicated `/settings/notifications` page with `ToggleRow` and `EmailPreviewCard` components using TanStack Query for notification preference mutations and test email sending. Removed inline notification section from `/settings/page.tsx`.

**Key decisions:**
- `column("generated_at")` used instead of `MetaDocument.generated_at` in `order_by(desc())` — pyright couldn't resolve `generated_at` as a SQLAlchemy column expression due to SQLModel type stubs.
- Email methods are non-fatal (try/except with structlog error, no re-raise) per RULE 1 compliance.
- MetaDocHistory fix: backend returns list directly not paginated response, so `res.items` changed to `res` directly.

**Gotchas:**
- pyright error "Argument of type datetime cannot be assigned to parameter column" — SQLModel field `generated_at: datetime` typed as Python `datetime` class not SQLAlchemy `Column`. Fixed with `column("generated_at")` string-based column reference.
- `res.items` property doesn't exist on API response — backend returns list directly.

**Tech debt noted:**
- `email_service.py` test coverage is 34% — EmailService methods were added but not fully tested in this story.
- Email templates hardcode brand colors in HTML inline styles — consider using CSS variables in a future template system.

---

## Sprint 33 — Legal Pages

> Privacy Policy, Terms of Service, Cookie Consent.
> Sprint 33 covers STORY-033.

### STORY-033 — Legal Pages
**Date:** 2026-04-02 | **Sprint:** 33 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 0 TypeScript errors, build passes (both pages SSG)
**Commit:** `b962e38`

**What was built:**
All legal pages and cookie consent were built in prior sprints as part of STORY-021 and other marketing work. Verified all 8 acceptance criteria are met: `/privacy` and `/terms` render as static routes with correct semantic HTML (`<main>`, `<article>`, logical heading order), metadata exports (`robots: { index: true, follow: true }`), and sitemap inclusion. Footer has `<nav aria-label="Legal navigation">` with `/privacy` and `/terms` links. CookieConsent component (`components/marketing/CookieConsent.tsx`) conditionally shows if `NEXT_PUBLIC_POSTHOG_KEY` is set, stores consent in localStorage key `ravenbase-cookie-consent`, and has Accept/Decline buttons with Privacy Policy link.

**Key decisions:**
- CookieConsent uses full-width fixed bottom banner style (not modal) — never blocks page interaction
- No PostHog integration exists yet — CookieConsent is future-proofed and will gate PostHog when added
- Legal pages use `prose prose-stone max-w-none` for consistent prose styling

**Gotchas:**
- PostHog not yet integrated — CookieConsent is ready but has nothing to gate yet

**Tech debt noted:**
- Placeholder legal copy needs human review before launch

---

## Sprint 34 — Referral System

> Referral codes, signup bonus, first-upload reward, Settings → Referrals page.
> Sprint 34 covers STORY-034.

### STORY-034 — Referral System
**Date:** 2026-04-02 | **Sprint:** 34 | **Phase:** B | **Repo:** ravenbase-api + ravenbase-web
**Quality gate:** ✅ clean — 350 tests passing, 0 ruff errors, 0 pyright errors
**Commit (backend):** `bda8cd3`
**Commit (migration):** `60e6686`
**Commit (frontend client):** `748b8df`

**What was built:**
Referral system with auto-generated referral codes (8 hex chars uppercase from UUID), +200 signup bonus for referees on code application, +200 first-upload reward for referrers, monthly cap of 50, and Settings → Referrals page with copy button and milestone timeline. ReferralTransaction model tracks all reward events. Two new API endpoints: GET /v1/account/referral (stats) and POST /v1/account/apply-referral (apply code). award_referrer_on_first_upload called synchronously inside parse_document and ingest_text for atomicity.

**Key decisions:**
- award_referrer_on_first_upload called synchronously inside parse_document (not a separate ARQ task) — ensures atomicity with source completion
- apply_referral_code silently ignores invalid codes (not an error to user) per AC-2
- Referral code lookup is case-insensitive (normalized to uppercase before DB query) per AC-10
- Monthly cap checked before awarding (prevents awarding then skipping)
- Migration is a merge of two diverging alembic branches (tuple down_revision)

**Gotchas:**
- Frontend Settings → Referrals page already existed before this story — only backend was built
- Pyright required `# type: ignore[attr-defined]` on `User.id.in_()` call (SQLAlchemy operator not recognized on typed str column)
- Pyright required datetime comparison fix: month_start changed from string to datetime object for SQLAlchemy comparison

**Tech debt noted:**
- No dedicated referral tests written yet (coverage 30%)

---

## Sprint 19 — Cold Data Lifecycle

> Inactivity CRON, activity middleware, 150/180-day purge.
> Sprint 19 covers STORY-037.

### STORY-037 — Cold Data Lifecycle — Inactivity Archival
**Date:** 2026-03-29 | **Sprint:** 19 | **Phase:** A | **Repo:** ravenbase-api
**Quality gate:** ✅ clean — 333 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `ee6299d`

**What was built:**
`ActivityTrackingMiddleware` intercepts every authenticated request and debounces `last_active_at` writes via a Redis key (once per user per 24h). `ColdDataService` implements two-phase inactivity logic: Phase 1 (`send_inactivity_warnings`) emails Free-tier users inactive 150–179 days using `EmailService` (Resend, lazy import) with `DataRetentionLog` deduplication; Phase 2 (`purge_inactive_users`) deletes Storage, Qdrant, Neo4j, and Postgres content rows (NOT the users row) for users inactive ≥180 days, then sets `is_archived=True` and `credits_balance=0`. The `cleanup_cold_data` ARQ CRON task fires every Sunday at 02:00 UTC via `WorkerSettings.cron_jobs`.

| Stat | Count |
|---|---|
| New models | 1 (`DataRetentionLog`) |
| New services | 2 (`ColdDataService`, `EmailService`) |
| New middleware | 1 (`ActivityTrackingMiddleware`) |
| New worker tasks | 1 (`cleanup_cold_data`) |
| Alembic migrations | 1 (`data_retention_logs` table) |
| Tests added | 31 (unit + integration) |

**Key decisions:**
- `delete_content_by_tenant` added to `DeletionService` (separate from GDPR `delete_postgres_by_tenant`) — never touches the `users` row, so archived user can still log in and re-upload.
- Redis debounce key `activity:{user_id}` with 24h TTL prevents a hot DB write on every API call; if Redis is unavailable the middleware falls back to a direct DB write (non-fatal).
- `DataRetentionLog` written per-user per-event for full audit trail; warning dedup queries check within the 180-day window to avoid re-sending after the window resets.
- Phase 2 rollback-on-step-failure (AC-14): any exception during multi-store deletion triggers `db.rollback()` and `continue` — user stays `is_archived=False` until the next CRON succeeds.
- `ADMIN_USER_IDS` env var used to skip admin accounts in both phases.

**Gotchas:**
- Pyright flags `User.is_archived.is_(False)` as an error because it sees `is_archived: bool` not as a SQLAlchemy column expression. Added `# type: ignore[attr-defined]` and `# type: ignore[operator]` on the affected WHERE clauses.
- `account.py` was calling `require_user(authorization)` but the signature had changed to `require_user(request, authorization)` — fixed the call to pass both arguments.
- Several pre-existing test files from earlier STORY-037 tasks had ruff E702 (semicolons) and I001 (import ordering) errors — fixed as part of quality gate.

**Tech debt noted:**
- `ActivityTrackingMiddleware` currently reads `request.state.user_id` which is set by other middleware/dependencies; relies on execution order being correct. Should add explicit guard logging if `user_id` is missing.
- Qdrant and Neo4j deletion counts are hardcoded to 0 in `DataRetentionLog` (AC-13) — the adapters don't return row counts. Consider returning counts from adapters in a future story if audit precision is needed.

---

## Sprint 20 — Auth Frontend

> Clerk auth pages, middleware, API fetch wrappers.
> Sprint 20 covers STORY-018-FE.

### STORY-018-FE — Clerk Auth Pages + Middleware
**Date:** 2026-03-30 | **Sprint:** 20 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 7 tests passing, 0 TypeScript errors
**Commit:** `24354c8`

**What was built:**
Clerk frontend auth layer. `/login` and `/register` pages use Clerk embedded `<SignIn />` / `<SignUp />` components with brand lockup above. Root `middleware.ts` intercepts all requests and redirects unauthenticated `/dashboard/*` visitors to `/login`. `ClerkProvider` added to root layout. `apiFetch` (server component wrapper) and `useApiFetch`/`useApiUpload` (client hooks) attach Clerk JWT to every API call. `QueryClientProvider` added to dashboard layout — prerequisite for all future TanStack Query usage. Brand components (`RavenbaseLogo`, `RavenbaseLockup`) updated: `color` prop added to Lockup, default size changed to `lg`, `aria-label` replaced with `aria-hidden="true"`. Also created `vitest.config.ts` with `@/` path alias — was missing from scaffold.

**Key decisions:**
- Skip link lives in root layout only — not duplicated in individual auth pages (root layout wraps all routes including `(auth)/`).
- Brand lockup uses `text-primary` wrapper class on auth pages — `currentColor` inherits foreground color, which on cream background reads correctly as forest green.
- `happy-dom` chosen over `jsdom` for vitest browser environment — `jsdom` has a CJS/ESM conflict with `@exodus/bytes` / `html-encoding-sniffer` that prevents test collection.
- `vitest.config.ts` created at project root to wire `@/` alias — Next.js configures this via tsconfig `paths` but vitest needs it explicitly in its vite config.

**Gotchas:**
- In Clerk v6 (`@clerk/nextjs ^6.0.0` resolving to `6.23.x`), `auth()` inside `clerkMiddleware` is **async**, not synchronous. The plan stated it was synchronous; TypeScript rejected `const { userId } = auth()` with "Property 'userId' does not exist on type 'Promise<...>'". Fixed by making the middleware callback `async` and adding `await auth()`.
- `jsdom` package conflicts with `@exodus/bytes` (ESM-only package required by `html-encoding-sniffer`). Use `happy-dom` instead — same API surface, no conflicts.
- vitest needs its own path alias config even though tsconfig already declares `@/*` paths.

**Tech debt noted:**
- `afterSignUpUrl="/dashboard"` is a temporary shortcut — the onboarding story (STORY-019) will replace this with a redirect that checks onboarding completion status.

---

## Sprint 24 — Chat UI

> Conversational memory chat with SSE streaming and citations.
> Sprint 24 covers STORY-027.

### STORY-027 — Conversational Memory Chat — Frontend
**Date:** 2026-03-30 | **Sprint:** 24 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 20 tests passing, 0 TypeScript errors
**Commit:** `b16a550`

**What was built:**
Chat page at `/chat` with SSE streaming via `fetch()` + `ReadableStream` reader (not EventSource — POST required). Messages stream token-by-token with animated ▌ cursor. Citations appear as clickable mono cards after response completes. Session sidebar shows history with load/delete. Model selector (Haiku/Sonnet). 402 response shows upgrade dialog. Mobile uses Sheet drawer for sessions. Empty state: "Ask me anything about your memories." TanStack Query for session list with 10s stale time.

**Key decisions:**
- Used raw `fetch()` with `ReadableStream.getReader()` instead of EventSource because SSE endpoint requires POST (EventSource only supports GET)
- Citation type matches `CitationItem` from STORY-026 backend: `{memory_id, content_preview, source_id}`
- 402 check happens BEFORE starting the stream reader to avoid consuming the response body
- Stream errors are caught and displayed inline (not console.error) with "Failed to get response. Try again."
- Session list invalidated after `done` event so sidebar updates with new session title
- Mobile layout uses `h-[100dvh]` and `pb-[max(1rem,env(safe-area-inset-bottom))]` per CLAUDE.md RULE 12/13

**Gotchas:**
- `(dashboard)` route group does not add a URL segment — `(dashboard)/chat` maps to `/chat`, not `/dashboard/chat`. All sidebar links and specs now use correct URLs (`/chat`, `/inbox`, `/graph`, etc.).
- `@testing-library/user-event` not installed — tests use `userEvent.setup()` + vitest-compatible assertions instead of jest-dom matchers
- `pb-[max(1rem,env(safe-area-inset-bottom))]` used directly in className (not `style={}`) — Tailwind arbitrary value syntax works with CSS calc/functions

**Tech debt noted:**
- No session title editing — session titles are auto-derived from first message (first 60 chars)
- Model credit cost not displayed next to model options (backend doesn't expose per-model cost in API response)

---

## Sprint 35 — Data Export + Admin Dashboard

> GDPR Article 20 data portability, Settings → Data page, final admin dashboard UI.
> Sprint 35 covers STORY-035.

### STORY-035 — Data Export / Right to Portability
**Date:** 2026-04-02 | **Sprint:** 35 | **Phase:** B | **Repo:** ravenbase-api + ravenbase-web
**Quality gate:** ✅ clean — 350 tests passing, 0 ruff errors, 0 pyright errors
**Commit:** `d1a71e3` (backend), `e245dab` (frontend)

**What was built:**
Backend: `ExportService` collects PostgreSQL (sources, meta_documents, profiles, chat_sessions), Neo4j (nodes + relationships, excluding Qdrant vectors per GDPR), and original Supabase Storage files into a ZIP at `exports/{user_id}/{timestamp}.zip`, generates 72-hour pre-signed download URL, sends completion email via `EmailService.send_export_complete()`, and sets Redis rate limit key `export:cooldown:{user_id}` with 24h TTL. Two new API endpoints: `POST /v1/account/export` (202, enqueues ARQ task) and `GET /v1/account/export/status`. `generate_user_export` ARQ task with partial failure handling (creates `PARTIAL_EXPORT.txt` if any component fails). Frontend: `Settings → Data` page fixed 7 bugs — format card icons now render, 429 rate limit toast, polling `enabled` flag uses `queryClient.getQueryData`, progress bar `rounded-full`, error display with dismiss button. Loading state skeleton fixed to `grid-cols-1 sm:grid-cols-3`.

**Key decisions:**
- `JobStatus` model uses `id` as primary key (not `job_id`) and stores result JSON in `message` field — followed `DeletionService` pattern exactly.
- Supabase `create_signed_url` returns `SignedUrlResponse` object with `.signed_url` attribute, not a plain string — used `getattr` with fallback to `str()`.
- All PostgreSQL queries use `db.execute(text(...))` not `db.exec()` — `exec()` has pyright overload issues with raw SQL.
- Progress callback inside `export_for_user` uses closure over `result` dict — avoids mutable default argument.
- Rate limit Redis key set inside ARQ task (not route handler) so it persists only on successful job completion.

**Gotchas:**
- `ExportFormat(str, Enum)` ruff UP042 error — changed to `ExportFormat(StrEnum)` from `enum` module.
- Parameter order error in `start_export`: `body` before `request` caused "non-default follows default" TypeError — reordered to `request, body, user`.
- `JobStatus` query in ARQ task used `job_id=` but the field is `id=` — fixed throughout.
- `create_signed_url` pyright error — Supabase client's `storage.from_().create_signed_url()` returns `SignedUrlResponse`, not string. Used `getattr(signed_url_response, "signed_url", None) or str(signed_url_response)`.
- Frontend `enabled` flag in `useQuery` was checking `exportMutation.data?.job_id` but job_id is stored via `queryClient.setQueryData`, not mutation data — broke polling. Fixed to use `queryClient.getQueryData(["export-job-id"])?.job_id`.

**Tech debt noted:**
- No dedicated export tests written yet (coverage gap).

---

## Sprint 36 — STORY-036-FE: Admin Dashboard UI

**Date:** 2026-04-02
**Sprint:** 36
**Phase:** B — Frontend
**Repo:** ravenbase-web

**Quality gate:** `npm run build` — ✅ 0 TypeScript errors, all 3 admin pages compiled (`/admin`, `/admin/users`, `/admin/users/[id]`)

**Commit:** `ce178c6`

**What was built:**
- Fixed API contract mismatches in all 3 admin pages against the live backend (`types.gen.ts` as source of truth)
- Stats page (`app/admin/page.tsx`): corrected `AdminStats` interface — `active_today`, `new_today`, `daily_llm_spend_usd`, `llm_spend_cap_usd`, `sources_today`, `metadocs_today`. Removed nonexistent fields. Added 6-card grid, proper LLM spend format (`$X.XXXX / $Y`), `<Link>` for navigation
- Users list (`app/admin/users/page.tsx`): fixed `AdminUserListResponse` paginated type, server-side search, client-side tier/status filtering, corrected toggle-active URL to `POST /v1/admin/users/${userId}/toggle-active` with `{ active: boolean }` body, added `StatusFilter` pills, skeleton table rows, `DropdownMenuSeparator`
- User detail (`app/admin/users/[id]/page.tsx`): fixed `recent_transactions`/`operation` field names, corrected toggle-active URL/body, added ban/unban confirmation dialog, restructured credit adjustment as proper dialog, added `balance_after` column, replaced `animate-pulse` divs with `Skeleton`
- Created missing `app/admin/users/[id]/loading.tsx` (RULE 10 compliance)
- Fixed layout.tsx: skip link + `id="main-content"` (RULE 16), red accent bar in header

**Key decisions:**
- Tier/status filtering is client-side — backend only exposes `q`/`page`/`page_size`
- Toggle-active uses path param, not body `user_id`
- `app/admin/middleware.ts` is dead code — layout.tsx handles auth redirect

**Gotchas:**
- Tailwind v4 canonical classes: `min-h-[44px]` → `min-h-11`, `min-w-[180px]` → `min-w-45`
- `AdminUserListResponse` has no `limit` field, only `total` and `page`

---

## Sprint 39 — Critical Bug Fixes

> EPIC-10 launch hardening: double Header/Footer, auth redirects, broken routes, memory leaks,
> admin/marketing page fixes, deployment config, and more.
> Sprint 39 covers STORY-039.

### STORY-039 — Critical Bug Fixes (BUG-001 through BUG-033)
**Date:** 2026-04-02 | **Sprint:** 39 | **Phase:** B | **Repo:** ravenbase-web + ravenbase-api
**Quality gate:** ✅ clean — 350 tests passing, 0 ruff errors, 0 pyright errors, 0 TypeScript errors (24 routes compiled)
**Commit:** `fbeaa2c` (api), `f249675` (web)

**What was built:**
Fixed 20+ production blockers across both repos. Key fixes: removed double Header/Footer renders on all marketing pages (layout.tsx already renders them); created `app/dashboard/page.tsx` (top-level, not inside route group) to redirect `/dashboard` → `/chat`; stripped `backdrop-blur-sm` from Header scroll state (design system violation); patched `middleware.ts` to redirect authenticated users from `/` to `/chat`; changed all OnboardingWizard completion redirects from `/dashboard` to `/chat`; fixed `DELETE /v1/account` call from Settings → Data (was showing success toast without calling any API — CRITICAL); added skip link to dashboard layout (WCAG 2.1 AA); fixed MemoryChat SSE reader leak via `readerRef`; clamped MemoryInbox `activeIndex` to `Math.max(0,...)` to prevent out-of-bounds; removed unimplemented `/search` and `/generate` Omnibar commands; made GraphQueryBar example clicks auto-execute; fixed admin progress bar to use `w-(--progress-width)` CSS custom property (Tailwind v4 canonical); fixed COLOR_OPTIONS in profiles page (removed duplicate `var(--accent)`, switched from inline `style={{ backgroundColor }}` to `className`); fixed `bg-white` in PricingToggle to `bg-secondary`; replaced fake testimonials with `null` render; fixed Header NAV_LINKS to use absolute anchor paths (`/#how-it-works`); validated checkout URL before redirect (BUG-033); fixed Dockerfile.api `--reload` → `--workers 2`.

**Key decisions:**
- `app/(dashboard)/page.tsx` CONFLICTS with `app/(marketing)/page.tsx` (both resolve to `/`) — correct location for the dashboard redirect is `app/dashboard/page.tsx` (outside any route group). This is a Next.js App Router constraint: route groups don't add URL segments but they also cannot host conflicting root-level routes.
- BUG-015 (Delete Account) was marked CRITICAL — it showed a success toast and did nothing. Fixed to call `DELETE /v1/account` via `apiFetch`, with loading state + error handling, then `router.push("/")` on success.
- MemoryChat SSE reader stored in `useRef<ReadableStreamDefaultReader>` (not `useState`) — avoids re-render loop. Cleanup via `useEffect` return that calls `readerRef.current?.cancel().catch(() => null)`.
- Tailwind v4 canonical: `[width:var(--progress-width)]` → `w-(--progress-width)` per IDE diagnostic.

**Gotchas:**
- Two route files resolving to `/` is a silent build error in Next.js — the error message says "two parallel pages that resolve to the same path" but doesn't name which two. Had to deduce that `(dashboard)/page.tsx` and `(marketing)/page.tsx` both resolve to `/`.
- `TestimonialsSection` replaced with `return null` — fake testimonials are a launch blocker per BUG-014.
- Settings loading.tsx skeleton structure was mismatched against actual page — replaced with accurate skeleton.

**Tech debt noted:**
- BUG-016/017/018/019/023/024/027/029/030 all deferred to STORY-043 (Final UX Polish Pass).

---

## Sprint 40 — Admin Bypass System

> Zero-credit access for admin users: backend bypass, GET /v1/users/me endpoint, frontend indicators.
> Sprint 40 covers STORY-040.

### STORY-040 — Admin Bypass System (ADMIN-001 through ADMIN-004)
**Date:** 2026-04-02 | **Sprint:** 40 | **Phase:** B | **Repo:** ravenbase-api + ravenbase-web
**Quality gate:** ✅ clean — 350 tests passing, 0 ruff errors, 0 pyright errors, 0 TypeScript errors
**Commit:** `fbeaa2c` (api), `f249675` (web)

**What was built:**
Full admin bypass system. Backend: `CreditService.deduct()` returns a zero-amount `CreditTransaction` with `balance_after=-1` (sentinel) for any `user_id` in `ADMIN_USER_IDS` env var — admin users never blocked by credit checks. New `GET /v1/users/me` endpoint (on `users_router` with prefix `/v1/users`) returns `{id, email, display_name, tier, credits_balance, preferred_model, is_admin, has_completed_onboarding}` — both flags computed at request time from env var and profile existence. `POST /v1/users/me/complete-onboarding` added as no-op idempotent endpoint. Frontend: Sidebar queries `GET /v1/users/me` and shows `◆ ADMIN_ACCESS` in the credits footer for admin users. Pricing page shows an admin bypass message (no tier cards, no upgrade CTAs) when `is_admin: true`.

**Key decisions:**
- `is_admin` computed from env var at request time — no DB field, no migration required.
- `users_router` prefix `/v1/users` is separate from `account.router` prefix `/v1/account` — both registered in `main.py`.
- `CreditTransaction.user_id` is `str` — Clerk IDs are strings; plan document's suggestion of `_uuid.UUID(user_id)` was wrong.
- `SystemProfile` is the correct model class name — aliased as `Profile` via `from src.models.profile import SystemProfile as Profile`.

**Gotchas:**
- `select` was used inside `get_current_user` without module-level import — added as lazy import `from sqlmodel import select as _select` inside function body (RULE 6).
- `complete_onboarding` endpoint uses `_user` (underscore prefix) to silence ruff ARG001 for unused parameter.
- Pyright `reportAttributeAccessIssue` on `Profile` import — class is `SystemProfile` not `Profile`.

**Tech debt noted:**
- No tests for the new `/v1/users/me` endpoint — add in STORY-043 or a future hardening story.

---

## Sprint 41 — Sources Page + UX Gaps + Deployment Config

> Wire IngestionDropzone into Sources Upload tab, create vercel.json, update next.config.mjs.
> Sprint 41 covers STORY-041.

### STORY-041 — Sources Page Upload + UX Gaps + Deployment Config
**Date:** 2026-04-02 | **Sprint:** 41 | **Phase:** B | **Repo:** ravenbase-web
**Quality gate:** ✅ clean — 0 TypeScript errors, 24 routes compiled
**Commit:** `f249675`

**What was built:**
Sources page Upload tab now renders `<IngestionDropzone>` with full upload flow: `POST /v1/ingest/upload` via `useApiUpload`, `<IngestionProgress sourceId={...}>` conditionally rendered after upload. Created `ravenbase-web/vercel.json` with 6 security headers (X-Content-Type-Options, X-Frame-Options DENY, X-XSS-Protection, Referrer-Policy, HSTS, Permissions-Policy), `Cache-Control: no-store` on `/api/(.*)` routes, and `/dashboard` → `/chat` redirect. Updated `next.config.mjs` with `images.remotePatterns` for `img.clerk.com`, `*.supabase.co`, and `images.unsplash.com` (required for production Vercel image optimization).

**Key decisions:**
- `vercel.json` redirect uses `permanent: false` (307) — same behavior as `app/dashboard/page.tsx`. Using 301 would cache in browser.
- `next.config.mjs` uses `remotePatterns` (not deprecated `domains`) — `domains` is removed in Next.js 15.
- `IngestionProgress` receives `sourceId` (not `jobId`) — matches SSE stream endpoint signature.

**Gotchas:**
- Sources page must use `useApiUpload` hook (client component) — cannot use `apiFetch` (server-only).
- `IngestionDropzone` requires `profileId?: string` from `useProfile()` context.

**Tech debt noted:**
- Sources page has no error boundary — add in STORY-043.
- `IngestionProgress` polling interval hardcoded at 2s.

---

## ✅ Backend Gate Checkpoint

**Date passed:** 2026-03-30
**make test result:** ✅ 333 passed, 0 failures
**make quality result:** ✅ 0 ruff errors, 0 pyright errors
**npm run generate-client result:** ✅ non-empty src/lib/api-client/ (9 files: types.gen.ts, services.gen.ts, schemas.gen.ts, core/); fixed --client flag: `axios` → `legacy/axios` for openapi-ts v0.53
**curl /health result:** ✅ API responds, Redis healthy; postgresql/qdrant/neo4j show errors in local dev (cloud services — expected; containers healthy per `docker compose ps`)

---

## ✅ Project Complete Checkpoint

_Filled in when all 37 stories are done._

**Date completed:** _not yet_
**Total duration:** _not yet_
**Total stories:** 37 / 37
**Hardest story (most sessions):** _fill in_
**Biggest surprise:** _fill in_
**Most important architectural decision:** _fill in_
