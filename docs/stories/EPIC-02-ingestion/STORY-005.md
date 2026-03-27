# STORY-005: File Upload Endpoint + Supabase Storage

**Epic:** EPIC-02 — Ingestion Pipeline
**Priority:** P0
**Complexity:** Medium
**Depends on:** STORY-002, STORY-004
**Type:** Backend
**Repo:** ravenbase-api

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-01-AC-1: POST /v1/ingest/upload accepts PDF and DOCX files up to 200 MB (pro) or 50 MB (free)
- FR-01-AC-2: Duplicate files (same SHA-256 hash per tenant) return status="duplicate" without re-processing
- FR-01-AC-3: Unsupported MIME types return 422 INVALID_FILE_TYPE
- FR-01-AC-4: Source record created in PostgreSQL with status PENDING → PROCESSING → INDEXING → COMPLETED transitions
- FR-01-AC-5: Chunks upserted to Qdrant with tenant_id in payload
- FR-01-AC-6: Progress published to Redis pub/sub at each status transition

## Component
COMP-01: IngestionPipeline

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/architecture/03-api-contract.md` — `POST /v1/ingest/upload` full request/response spec
> 3. `docs/architecture/05-security-privacy.md` — MIME validation, magic bytes, rate limiting patterns
> 4. `docs/architecture/02-database-schema.md` — Source model, SourceStatus constants
> 5. `docs/architecture/04-background-jobs.md` — enqueue pattern for ARQ

---

## User Story
As a user, I want to upload a PDF and immediately receive a job ID so I can track processing progress.

## Context
- API contract: `architecture/03-api-contract.md` — `POST /v1/ingest/upload`
- Security: `architecture/05-security-privacy.md` — MIME validation, size limits
- Data models: `architecture/02-database-schema.md` — Source table, SourceStatus

## Acceptance Criteria
- [ ] AC-1: `POST /v1/ingest/upload` accepts `multipart/form-data` with `file` field
- [ ] AC-2: MIME type validated using magic bytes (not just Content-Type header)
- [ ] AC-3: File size enforced: 50MB free, 200MB pro (tier from JWT)
- [ ] AC-4: SHA-256 deduplication: if file already ingested by this user, return existing `source_id` with `duplicate: true`
- [ ] AC-5: File stored in Supabase Storage at path `/{tenant_id}/{source_id}/{original_filename}`
- [ ] AC-6: `Source` record created in PostgreSQL with `status=pending`
- [ ] AC-7: `ingestion` job enqueued to ARQ, returns `{job_id, source_id, status: "queued"}`
- [ ] AC-8: Unsupported file type returns `422` with `ErrorCode.INVALID_FILE_TYPE`
- [ ] AC-9: Rate limit: 10 uploads/hour for free users, 50/hour for pro

## Technical Notes

### Files to Create
- `src/api/routes/ingest.py` — upload + text endpoints
- `src/adapters/storage_adapter.py` — wraps Supabase Storage client
- `src/schemas/ingest.py` — UploadResponse, IngestTextRequest
- `tests/integration/api/test_ingest_upload.py`

### Architecture Constraints
- Route must call service, not directly call storage
- `source_id` generated as UUID before storage (used as storage path component)
- Ingestion service is the only place that knows about Supabase Storage

### Upload Response Schema
```python
# src/schemas/ingest.py
from pydantic import BaseModel
from uuid import UUID

class UploadResponse(BaseModel):
    job_id: str
    source_id: UUID
    status: str           # "queued" | "duplicate"
    duplicate: bool = False
```

### Magic Bytes Validation Pattern
```python
MAGIC_BYTES: dict[bytes, str] = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats",  # docx, xlsx, pptx
}

def validate_file_type(content: bytes) -> str:
    for magic, mime in MAGIC_BYTES.items():
        if content.startswith(magic):
            return mime
    raise HTTPException(
        status_code=422,
        detail={"code": ErrorCode.INVALID_FILE_TYPE, "message": "Unsupported file type"},
    )
```

### SHA-256 Deduplication Pattern
```python
import hashlib

file_hash = hashlib.sha256(content).hexdigest()
existing = await db.exec(
    select(Source).where(
        Source.user_id == tenant_id,
        Source.sha256_hash == file_hash,
    )
).first()
if existing:
    return UploadResponse(
        job_id="",
        source_id=existing.id,
        status="duplicate",
        duplicate=True,
    )
```

## Definition of Done
- [ ] Upload returns 202 with `{job_id, source_id, status: "queued"}`
- [ ] Magic bytes validation rejects unsupported files with 422
- [ ] SHA-256 deduplication returns existing source_id with `duplicate: true`
- [ ] File stored in Supabase Storage at correct path
- [ ] Source record in PostgreSQL with `status=pending`
- [ ] ARQ job enqueued (verify with Redis CLI)
- [ ] `make quality` passes (0 errors)

## Testing This Story

```bash
# Integration test:
uv run pytest tests/integration/api/test_ingest_upload.py -v

# Manual upload test:
curl -X POST http://localhost:8000/v1/ingest/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@tests/fixtures/sample.pdf"
# Expected: 202 {"job_id": "...", "source_id": "...", "status": "queued", "duplicate": false}

# Test deduplication (upload same file twice):
curl -X POST http://localhost:8000/v1/ingest/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@tests/fixtures/sample.pdf"
# Expected: 202 {"job_id": "", "source_id": "<same UUID>", "status": "duplicate", "duplicate": true}

# Test invalid file type:
curl -X POST http://localhost:8000/v1/ingest/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@tests/fixtures/test.exe"
# Expected: 422 {"detail": {"code": "INVALID_FILE_TYPE", "message": "Unsupported file type"}}

# Quality:
make quality
```

**Passing result:** Upload returns 202 with job_id. File stored in Supabase Storage. Source record created with status=pending. Duplicate upload returns existing source_id with `duplicate: true`.

---

## Agent Implementation Brief

```
Implement STORY-005: File Upload Endpoint + Supabase Storage.

Read first:
1. CLAUDE.md (architecture rules — RULE 3: heavy work in ARQ, RULE 4: schemas first)
2. docs/architecture/03-api-contract.md (POST /v1/ingest/upload request/response spec)
3. docs/architecture/05-security-privacy.md (MIME validation, magic bytes, rate limits)
4. docs/architecture/02-database-schema.md (Source model, SourceStatus constants)
5. docs/architecture/04-background-jobs.md (ARQ enqueue pattern)
6. docs/stories/EPIC-02-ingestion/STORY-005.md (this file)

Key constraints:
- Write UploadResponse Pydantic schema in src/schemas/ingest.py FIRST
- Magic bytes validation (not Content-Type header) for MIME detection
- SHA-256 hash computed before storage for deduplication check
- source_id = uuid4() generated BEFORE uploading to Supabase (used as path component)
- Route enqueues ARQ job and returns immediately — no synchronous processing
- Rate limiting via Redis counter keyed on tenant_id (10/hr free, 50/hr pro)

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# 1. Quality gate:
make quality && make test       # backend
npm run build && npm run test   # frontend (if applicable)

# 2. Commit:
git add -A && git commit -m "feat(ravenbase): STORY-005 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-005"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-005
git add docs/stories/epics.md && git commit -m "docs: mark STORY-005 complete"
```
