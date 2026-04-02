# COMP-01: IngestionPipeline

> **Component ID:** BE-COMP-01
> **Epic:** EPIC-02 — Ingestion Pipeline
> **Stories:** STORY-005, STORY-006, STORY-007, STORY-008, STORY-028
> **Type:** Backend

---

## Goal

The IngestionPipeline is the entry point for all user data. It accepts diverse input types, processes them asynchronously via ARQ workers, and deposits structured chunks into Qdrant for semantic search. The pipeline owns the full ingestion lifecycle from HTTP request to Qdrant upsert.

---

## Product Requirements

1. **File Upload Endpoint:** `POST /v1/ingest/upload` accepts `multipart/form-data` with a `file` field. Accepts PDF and DOCX files up to 50MB (free tier) or 200MB (pro tier). Returns `{job_id, source_id, status: "queued"}` immediately.

2. **Magic Bytes Validation:** MIME type is validated using magic bytes (not just Content-Type header). Unsupported files return `422 INVALID_FILE_TYPE`.

3. **SHA-256 Deduplication:** If a file with the same SHA-256 hash already exists for the same user, return the existing `source_id` with `duplicate: true` without re-processing.

4. **Supabase Storage:** Files are stored at path `/{tenant_id}/{source_id}/{original_filename}` in Supabase Storage.

5. **Source Record Creation:** A `Source` record is created in PostgreSQL with `status=pending`. Status transitions follow: `PENDING → PROCESSING → INDEXING → COMPLETED`.

6. **Docling Parse + Chunk + Embed Worker:** The `parse_document` ARQ task processes PDFs using Docling with `pypdfium2` backend (images disabled). Chunks are 512-token with 50-token overlap, preserving paragraph boundaries. Embeddings are generated via OpenAI `text-embedding-3-small` in batches of 100 (never one-by-one).

7. **Content Moderation:** Before Docling processing, the first extracted text preview (up to 4,000 characters) is passed to `ModerationAdapter().check_content()`. Hard-reject categories: source marked `failed` with `User.is_active = False`. Soft-reject: source marked `failed` only. If moderation API is unavailable: log warning and continue processing (fail open).

8. **Progress Publishing:** Job progress is published to Redis pub/sub channel `job:progress:{source_id}` at each stage (0%, 25%, 50%, 75%, 100%).

9. **ARQ Job Chaining:** After `parse_document` completes successfully, `graph_extraction` job is automatically enqueued to the ARQ worker.

10. **Corrupted File Handling:** Corrupted or unreadable PDFs: task marks source as `failed`, logs error, does NOT retry (to avoid billing waste).

11. **SSE Progress Stream:** `GET /v1/ingest/stream/{source_id}?token=` returns `text/event-stream`. Token is validated via `verify_token_query_param` (Clerk JWT as query param). Stream emits `data: {progress_pct, message, status}` events. Stream closes automatically when status is `completed` or `failed`. Client disconnect does not cause server error.

12. **Text Quick-Capture:** `POST /v1/ingest/text` accepts `{content, profile_id, tags}` JSON body. Text up to 50,000 characters accepted; over limit returns `422 TEXT_TOO_LONG`. Source record created with `file_type="direct_input"`. Text is searchable via `POST /v1/search` within 15 seconds of ingestion.

13. **Omnibar `/ingest` Command:** The Omnibar component supports `/ingest [text]` syntax. Pressing Enter after typing captures the text and shows a confirmation toast "Captured to [Profile Name]" within 2 seconds.

14. **Rate Limiting:** 10 uploads/hour for free users, 50/hour for pro users. Enforced via Redis counter keyed on tenant_id.

15. **Graph Extraction Trigger:** `graph_extraction` job is automatically enqueued after `COMPLETED` status is set — this triggers COMP-02 (GraphEngine) entity extraction.

16. **AI Chat Context Import:** `GET /v1/ingest/import-prompt?profile_id=` returns `{prompt_text, detected_concepts[]}` — a personalized extraction prompt based on the user's existing Neo4j Concept nodes. If user has no concepts yet, returns a generic extraction prompt (not a 404). Text input area accepts up to 100,000 characters.

---

## Admin Bypass

**Ingestion credit cost:** 1 credit per page of PDF content. Text ingest: 0 credits (always free).

Admin users (identified by `ADMIN_USER_IDS` env var): `CreditService.deduct()` returns a zero-amount transaction — no actual credits are consumed during file processing. The ingestion pipeline itself runs identically for admin users.

**PDF upload admin bypass:**
- Admin uploads PDF → `parse_document` worker runs → Docling parses → chunks embedded → Qdrant upsert
- Credit deduction step: `CreditService.deduct(user_id, pages, "ingestion")` → returns `amount=0` for admin
- Balance unchanged; `credit_transactions` row has `operation="admin_bypass:ingestion"`

**Text ingest:** always 0 credits for all users — no bypass needed.

See `BE-COMP-06-CreditSystem.md` for the admin bypass implementation in `CreditService`.

---

## Criteria and Tests

| Criterion | Test |
|---|---|
| Upload returns 202 with job_id | `POST /v1/ingest/upload` with valid PDF → 202 with `job_id` |
| Magic bytes validation rejects unsupported files | Upload `.exe` file → 422 `INVALID_FILE_TYPE` |
| SHA-256 deduplication returns existing source_id | Upload same file twice → second returns `duplicate: true` |
| Source status transitions correctly | Poll `GET /v1/sources/{id}` → transitions `pending → processing → indexing → completed` |
| SSE stream emits progress events | Connect to SSE → receive events at 0%, 25%, 50%, 75%, 100% |
| SSE stream closes on completed/failed | After `completed` status → SSE connection closes cleanly |
| Text ingest rejects > 50,000 chars | `POST /v1/ingest/text` with 50,001 chars → 422 `TEXT_TOO_LONG` |
| Omnibar `/ingest` shows confirmation toast | Type `/ingest Hello world` → press Enter → toast "Captured to..." appears |
| Import prompt handles empty concepts | New user calls `GET /v1/ingest/import-prompt` → returns generic prompt |
| 10-page PDF completes within 60s | Upload 10-page PDF → `source.status = completed` within 60 seconds |
| Graph extraction enqueued after completion | After `completed` → check Redis queue → `graph_extraction` job exists |

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-005](../stories/EPIC-02-ingestion/STORY-005.md) | File Upload Endpoint + Supabase Storage | Backend | `POST /v1/ingest/upload` with magic bytes validation, SHA-256 dedup, Supabase Storage |
| [STORY-006](../stories/EPIC-02-ingestion/STORY-006.md) | Docling Parse + Chunk + Embed Worker | Backend | ARQ task: Docling → chunking → embedding → Qdrant upsert |
| [STORY-007](../stories/EPIC-02-ingestion/STORY-007.md) | SSE Progress Stream | Cross-repo | Redis pub/sub → SSE streaming to frontend `IngestionProgress` component |
| [STORY-008](../stories/EPIC-02-ingestion/STORY-008.md) | Text Quick-Capture (Omnibar /ingest) | Cross-repo | `POST /v1/ingest/text` + Omnibar `/ingest` command |
| [STORY-028](../stories/EPIC-09-memory-intelligence/STORY-028.md) | AI Chat Context Import Helper | Cross-repo | `GET /v1/ingest/import-prompt` for importing AI chat exports |

---

## Subcomponents

The IngestionPipeline decomposes into 4 subcomponents, each matching 1-2 stories.

---

### SUBCOMP-01A: File Upload API

**Stories:** STORY-005
**Files:** `src/api/routes/ingest.py`, `src/adapters/storage_adapter.py`, `src/schemas/ingest.py`

#### Details
The file upload API is the HTTP entry point for the ingestion pipeline. It validates the file, stores it in Supabase Storage, creates a PostgreSQL `Source` record, and enqueues an ARQ job for async processing. The API returns immediately with a `job_id` — no synchronous processing of the file content.

#### Criteria of Done
- [ ] `POST /v1/ingest/upload` accepts `multipart/form-data` with `file` field
- [ ] MIME type validated using magic bytes (not Content-Type header)
- [ ] File size enforced: 50MB free, 200MB pro (tier from JWT)
- [ ] SHA-256 deduplication: same file for same user → return existing `source_id` with `duplicate: true`
- [ ] File stored in Supabase Storage at `/{tenant_id}/{source_id}/{original_filename}`
- [ ] `Source` record created in PostgreSQL with `status=pending`
- [ ] ARQ `parse_document` job enqueued, returns `{job_id, source_id, status: "queued"}`
- [ ] Unsupported file type returns `422 INVALID_FILE_TYPE`
- [ ] Rate limit: 10 uploads/hour free, 50/hour pro

#### Checklist
- [ ] Magic bytes validation pattern implemented (check `content[:4]` against known headers)
- [ ] SHA-256 hash computed before storage for deduplication
- [ ] `source_id` = `uuid4()` generated BEFORE uploading to Supabase (used as path component)
- [ ] Route enqueues ARQ job and returns immediately (no `await` on heavy work)
- [ ] `UploadResponse` Pydantic schema defined in `src/schemas/ingest.py`
- [ ] `ErrorCode.INVALID_FILE_TYPE` added to `src/core/errors.py`

#### Testing
```bash
# Happy path:
curl -X POST http://localhost:8000/v1/ingest/upload \
  -H "Authorization: Bearer TOKEN" -F "file=@sample.pdf"
# Expected: 202 {"job_id": "...", "source_id": "...", "status": "queued"}

# Deduplication:
curl -X POST http://localhost:8000/v1/ingest/upload \
  -H "Authorization: Bearer TOKEN" -F "file=@sample.pdf"
# Expected: 202 {"duplicate": true, "source_id": "<same UUID>"}

# Invalid file:
curl -X POST http://localhost:8000/v1/ingest/upload \
  -H "Authorization: Bearer TOKEN" -F "file=@test.exe"
# Expected: 422 {"code": "INVALID_FILE_TYPE"}
```

---

### SUBCOMP-01B: Docling Parse + Chunk + Embed Worker

**Stories:** STORY-006
**Files:** `src/workers/ingestion_tasks.py`, `src/adapters/docling_adapter.py`, `src/adapters/openai_adapter.py`, `src/services/ingestion_service.py`

#### Details
The `parse_document` ARQ task is the core processing engine. It runs Docling on uploaded PDFs, splits content into chunks, generates OpenAI embeddings, and upserts chunks to Qdrant. The task publishes progress to Redis at each stage and chains the `graph_extraction` job on completion. Content moderation is checked before Docling runs.

#### Criteria of Done
- [ ] `parse_document` ARQ task processes a PDF and produces chunks
- [ ] Docling uses `generate_page_images=False`, `generate_picture_images=False` for speed
- [ ] Chunking: 512-token chunks with 50-token overlap, preserving paragraph boundaries
- [ ] Embeddings via OpenAI `text-embedding-3-small` in batches of 100
- [ ] Chunks upserted to Qdrant with `tenant_id`, `source_id`, `chunk_id`, `profile_id`, `page_number`, `created_at`
- [ ] Source status updated: `pending → processing → indexing → completed`
- [ ] Progress published to Redis `job:progress:{source_id}` at each stage
- [ ] Corrupted PDF: `status=failed`, log error, no retry
- [ ] 10-page PDF completes within 60 seconds (no GPU)
- [ ] Content moderation: hard-reject sets `User.is_active=False`, soft-reject marks `failed`
- [ ] `graph_extraction` job enqueued after `COMPLETED`

#### Checklist
- [ ] Docling import inside function body (`# noqa: PLC0415`) — never at module level
- [ ] OpenAI embedding calls batched in groups of 100
- [ ] Blocking Docling code runs in `run_in_executor` — never blocks the event loop
- [ ] `ModerationAdapter().check_content()` called before Docling with 4,000 char preview
- [ ] Source status transitions: `PENDING → PROCESSING → INDEXING → COMPLETED`
- [ ] `publish_progress()` called at 0%, 25%, 50%, 75%, 100%
- [ ] `enqueue_job("graph_extraction", ...)` called after `COMPLETED`
- [ ] Failed source: `status=failed`, log with structlog, do NOT re-raise

#### Testing
```bash
# Verify Qdrant chunks after ingestion:
# Connect to Qdrant dashboard at http://localhost:6333/dashboard
# Expected: chunks visible with correct tenant_id payload

# Check ARQ job queue after upload:
redis-cli LRANGE arq:queue:default 0 -1
# Expected: graph_extraction job enqueued

# Corrupted PDF:
curl -X POST http://localhost:8000/v1/ingest/upload \
  -H "Authorization: Bearer TOKEN" -F "file=@corrupted.pdf"
# Expected: status=failed in sources table, no retry
```

---

### SUBCOMP-01C: SSE Progress Stream

**Stories:** STORY-007
**Files:** `src/api/routes/ingest.py` (SSE endpoint), `src/api/dependencies/auth.py` (`verify_token_query_param`), `components/domain/IngestionProgress.tsx`, `hooks/use-sse.ts`

#### Details
The SSE progress stream delivers real-time ingestion status to the frontend. The backend subscribes to Redis pub/sub and re-streams events to the browser via Server-Sent Events. The frontend `IngestionProgress` component uses the browser-native `EventSource` API to receive progress updates and display a progress bar. The `use-sse.ts` hook is reusable across multiple SSE streams (IngestionProgress, Workstation).

#### Criteria of Done
- [ ] `GET /v1/ingest/stream/{source_id}?token=` returns `text/event-stream`
- [ ] Token validated via `verify_token_query_param` (JWT in `?token=` query param)
- [ ] SSE stream emits `data:` events with `{progress_pct, message, status}`
- [ ] Stream closes automatically when status is `completed` or `failed`
- [ ] Client disconnect does not cause server error (pubsub.unsubscribe in `finally`)
- [ ] Frontend `IngestionProgress` component subscribes to SSE and updates progress bar
- [ ] Frontend shows correct states: idle → uploading → processing → complete/error

#### Checklist
- [ ] SSE uses `sse-starlette` (already in dependencies)
- [ ] Token passed as query param (`?token=`) — `EventSource` cannot set headers
- [ ] Redis pub/sub subscribe wrapped in `try/finally` — always `unsubscribe` on disconnect
- [ ] `EventSourceResponse` with `event_generator()` async function
- [ ] `verify_token_query_param` added to `src/api/dependencies/auth.py`
- [ ] Frontend `use-sse.ts` hook is reusable (not embedded in a component)
- [ ] Frontend `IngestionProgress` uses shadcn `Progress` component

#### Testing
```bash
# Manual SSE test:
TOKEN="clerk_token"
SOURCE_ID="source_uuid"
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8000/v1/ingest/stream/${SOURCE_ID}?token=${TOKEN}"
# Expected events:
# data: {"progress_pct": 0, "status": "processing"}
# data: {"progress_pct": 25, "status": "processing"}
# data: {"progress_pct": 100, "status": "completed"}
# Then connection closes
```

---

### SUBCOMP-01D: Text Quick-Capture + AI Chat Import

**Stories:** STORY-008, STORY-028
**Files:** `POST /v1/ingest/text` endpoint, `GET /v1/ingest/import-prompt` endpoint, `components/domain/Omnibar.tsx`, `components/domain/ImportFromAIChat.tsx`

#### Details
Text quick-capture enables users to paste text directly into the Omnibar and have it immediately ingested and indexed. The `/ingest [text]` slash command accepts up to 50,000 characters and creates a `Source` record with `file_type="direct_input"`. The AI Chat Import Helper (`STORY-028`) generates a personalized extraction prompt based on the user's existing knowledge graph concepts, which they run inside any AI chat and paste back for ingestion.

#### Criteria of Done (STORY-008)
- [ ] `POST /v1/ingest/text` accepts `{content, profile_id, tags}` JSON body
- [ ] Text up to 50,000 characters; over limit returns `422 TEXT_TOO_LONG`
- [ ] Source record created with `file_type="direct_input"`
- [ ] Text is searchable via `POST /v1/search` within 15 seconds
- [ ] Omnibar `/ingest [text]` command works with confirmation toast

#### Criteria of Done (STORY-028)
- [ ] `GET /v1/ingest/import-prompt?profile_id=` returns `{prompt_text, detected_concepts[]}`
- [ ] Personalized prompt based on user's existing Neo4j Concept nodes
- [ ] New user (no concepts): returns generic extraction prompt (not a 404)
- [ ] Frontend tabs: "Upload Files" / "Import from AI Chat" on `/sources`
- [ ] Copy button copies prompt with 2-second "Copied ✓" feedback
- [ ] Paste + Submit calls `/v1/ingest/text` and shows SSE progress
- [ ] Profile selector in Import tab; text area accepts up to 100,000 characters

#### Checklist (STORY-008)
- [ ] `ingest_text` ARQ task added (no Docling — simple text chunking + embed)
- [ ] `TextIngestRequest` schema in `src/schemas/ingest.py`
- [ ] `ErrorCode.TEXT_TOO_LONG` raised if `len(content) > 50_000`
- [ ] `file_type="direct_input"` set on Source record
- [ ] Omnibar `/ingest` command routes to ingest handler

#### Checklist (STORY-028)
- [ ] `ImportPromptResponse` schema in `src/schemas/ingest.py`
- [ ] Neo4j query to fetch existing Concept nodes for tenant
- [ ] Personalized prompt includes concept list; generic prompt if no concepts
- [ ] Frontend `ImportFromAIChat` tab added to `/sources`
- [ ] `GeneratedPromptBox` with Clipboard API copy + 2s feedback

#### Testing (STORY-008)
```bash
# Happy path:
curl -X POST http://localhost:8000/v1/ingest/text \
  -H "Authorization: Bearer TOKEN" \
  -d '{"content": "I use TypeScript.", "profile_id": null, "tags": []}'
# Expected: 202 {"status": "queued"}

# Character limit:
curl -X POST http://localhost:8000/v1/ingest/text \
  -H "Authorization: Bearer TOKEN" \
  -d "{\"content\": \"$(python3 -c 'print(\"a\"*50001))\"}"
# Expected: 422 {"code": "TEXT_TOO_LONG"}
```

#### Testing (STORY-028)
```bash
# User with concepts:
curl "http://localhost:8000/v1/ingest/import-prompt?profile_id=UUID" \
  -H "Authorization: Bearer TOKEN"
# Expected: {"prompt_text": "...Focus especially on: Python, TypeScript...", "detected_concepts": ["Python", "TypeScript"]}

# New user (no concepts):
curl "http://localhost:8000/v1/ingest/import-prompt" \
  -H "Authorization: Bearer TOKEN"
# Expected: {"prompt_text": "...Summarize all key topics...", "detected_concepts": []}
```
