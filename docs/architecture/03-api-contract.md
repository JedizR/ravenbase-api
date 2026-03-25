# Architecture — 03. API Contract

> **Cross-references:** `architecture/00-system-overview.md` | `architecture/02-database-schema.md`
>
> **AGENT NOTE:** This is the authoritative API specification. FastAPI auto-generates `/openapi.json` from Pydantic models. Regenerate the frontend client after any schema change: `npm run generate-client`.

---

## Global Conventions

- **Base URL:** `https://api.ravenbase.app/v1`
- **Auth:** All endpoints require `Authorization: Bearer {clerk_jwt}` except `/health`
- **Content-Type:** `application/json` (except file upload: `multipart/form-data`)
- **Tenant isolation:** `tenant_id` extracted from JWT by `require_user` dependency — never passed in request body
- **Error format:** `{"detail": {"code": "ERROR_CODE", "message": "Human-readable message"}}`
- **Pagination:** List endpoints return `PaginatedResponse[T]` with `items`, `total`, `page`, `page_size`
- **Timestamps:** All timestamps in ISO 8601 UTC format

---

## Shared Schemas

```python
# src/schemas/common.py
from pydantic import BaseModel
from typing import Generic, TypeVar
from uuid import UUID
from datetime import datetime

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool

class JobResponse(BaseModel):
    job_id: str
    status: str                    # "queued" | "active" | "completed" | "failed"
    progress_pct: int              # 0-100
    message: str | None = None
    created_at: datetime
    updated_at: datetime
```

---

## Ingestion Endpoints (`/v1/ingest`)

### `POST /v1/ingest/upload`
Upload a file for background processing.

**Request:** `multipart/form-data`
```
file:       File (required) — PDF, TXT, MD, JSON, ZIP
profile_id: UUID (optional) — assign to specific System Profile
```

**Validation rules:**
- Allowed MIME types: `application/pdf`, `text/plain`, `text/markdown`, `application/json`, `application/zip`
- Magic bytes validation (not just MIME header)
- Max file size: 50MB (free), 200MB (pro)
- Duplicate detection: if SHA-256 hash matches existing source for this user, return existing source_id

**Response `202 Accepted`:**
```json
{
  "job_id": "arq:job:uuid",
  "source_id": "uuid",
  "status": "queued",
  "duplicate": false
}
```

---

### `POST /v1/ingest/text`
Immediately ingest plain text (Omnibar quick-capture).

**Request:**
```json
{
  "content": "string (required, max 50000 chars)",
  "profile_id": "uuid (optional)",
  "tags": ["string"]
}
```

**Response `202 Accepted`:**
```json
{
  "job_id": "arq:job:uuid",
  "source_id": "uuid",
  "status": "queued"
}
```

---

### `GET /v1/ingest/status/{job_id}`
Poll job status. Use SSE stream for real-time updates.

**Response `200`:**
```json
{
  "job_id": "string",
  "status": "queued | active | completed | failed",
  "progress_pct": 45,
  "message": "Extracting entities...",
  "source_id": "uuid",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

---

### `GET /v1/ingest/stream/{job_id}`
SSE stream for real-time ingestion progress.

**Response:** `text/event-stream`
```
data: {"progress_pct": 10, "message": "Parsing document..."}
data: {"progress_pct": 40, "message": "Generating embeddings..."}
data: {"progress_pct": 70, "message": "Building knowledge graph..."}
data: {"progress_pct": 100, "message": "Complete", "status": "completed"}
```

**Auth:** Token passed as query param `?token=` (EventSource cannot set headers)

---

## Source Management Endpoints (`/v1/sources`)

### `GET /v1/sources`
List all sources for current user.

**Query params:** `profile_id`, `status`, `file_type`, `page`, `page_size`

**Response `200`:** `PaginatedResponse[SourceResponse]`
```json
{
  "items": [{
    "id": "uuid",
    "original_filename": "resume_2023.pdf",
    "file_type": "pdf",
    "status": "completed",
    "chunk_count": 42,
    "node_count": 15,
    "profile_id": "uuid",
    "ingested_at": "ISO8601",
    "file_size_bytes": 204800
  }],
  "total": 7,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

---

### `DELETE /v1/sources/{source_id}`
Delete a source and all derived data (cascade).

**Response `202 Accepted`:**
```json
{
  "job_id": "arq:job:uuid",
  "message": "Deletion queued. All embeddings and graph nodes will be purged within 60 seconds."
}
```

**Cascade order (deletion_worker):**
1. Delete from Supabase Storage
2. Delete chunks from Qdrant (by source_id filter)
3. Delete Memory nodes + edges from Neo4j
4. DELETE from PostgreSQL sources, job_statuses

---

## Search Endpoint (`/v1/search`)

### `POST /v1/search`
Hybrid semantic + keyword search over user's knowledge base.

**Request:**
```json
{
  "query": "string (required)",
  "profile_id": "uuid (optional — scopes search)",
  "date_from": "ISO8601 (optional)",
  "date_to": "ISO8601 (optional)",
  "limit": 10,
  "include_graph_context": true
}
```

**Response `200`:**
```json
{
  "results": [{
    "chunk_id": "uuid",
    "content": "string",
    "score": 0.94,
    "source": {
      "id": "uuid",
      "filename": "resume_2023.pdf",
      "file_type": "pdf"
    },
    "memory_id": "uuid",
    "graph_context": {
      "concepts": ["React", "TypeScript", "Frontend"],
      "temporal_links": []
    }
  }],
  "total_found": 23,
  "query_time_ms": 187
}
```

---

## Conflict Endpoints (`/v1/conflicts`)

### `GET /v1/conflicts`
List pending conflicts for Memory Inbox.

**Query params:** `status=pending`, `profile_id`, `page`, `page_size`

**Response `200`:** `PaginatedResponse[ConflictResponse]`
```json
{
  "items": [{
    "id": "uuid",
    "incumbent_content": "I use React for frontend development",
    "challenger_content": "I now exclusively use Vue.js for all frontend work",
    "ai_classification": "CONTRADICTION",
    "ai_proposed_resolution": "Update primary frontend framework to Vue.js. Tag React as Past Skill.",
    "confidence_score": 0.94,
    "incumbent_source": {"filename": "chat_export_2022.json", "ingested_at": "ISO8601"},
    "challenger_source": {"filename": "notes_march_2024.md", "ingested_at": "ISO8601"},
    "created_at": "ISO8601"
  }],
  "total": 3
}
```

---

### `POST /v1/conflicts/{conflict_id}/resolve`
Resolve a conflict with one of three flows.

**Request:**
```json
{
  "action": "ACCEPT_NEW | KEEP_OLD | CUSTOM",
  "custom_text": "string (required if action=CUSTOM)"
}
```

**Response `200`:**
```json
{
  "conflict_id": "uuid",
  "status": "resolved_accept_new",
  "graph_mutations": {
    "superseded_memory_id": "uuid",
    "active_memory_id": "uuid",
    "new_tags": ["Past Skill: React", "Current: Vue.js"]
  }
}
```

---

### `POST /v1/conflicts/{conflict_id}/undo`
Undo the last resolution (within 30s undo window).

**Response `200`:**
```json
{"conflict_id": "uuid", "status": "pending", "message": "Resolution undone successfully."}
```

---

## Graph Endpoints (`/v1/graph`)

### `GET /v1/graph/nodes`
Return all graph nodes for the Graph Explorer visualization.

**Query params:** `profile_id`, `node_types` (comma-separated), `limit=200`

**Response `200`:**
```json
{
  "nodes": [{
    "id": "uuid",
    "label": "React",
    "type": "concept",
    "properties": {"first_seen": "2021", "last_seen": "2023", "is_valid": true},
    "memory_count": 12
  }],
  "edges": [{
    "source": "uuid",
    "target": "uuid",
    "type": "RELATES_TO",
    "properties": {"weight": 0.8}
  }]
}
```

---

### `GET /v1/graph/neighborhood/{node_id}`
Return N-hop neighborhood for Graph Explorer node click.

**Query params:** `hops=2`, `limit=50`

**Response:** Same shape as `/v1/graph/nodes` but scoped to neighborhood.

---

## Meta-Document Endpoints (`/v1/metadoc`)

### `POST /v1/metadoc/generate`
Generate a Meta-Document. Returns job_id; client subscribes to SSE stream.

**Request:**
```json
{
  "prompt": "Generate a 1-page resume for a Senior Full-Stack Next.js role",
  "profile_id": "uuid (optional)",
  "model": "haiku | sonnet (optional — defaults to user's preferred_model setting)"
}
```

> If `model` is omitted, the user's `preferred_model` setting is used.
> Valid values: `"haiku"` → `claude-haiku-4-5-20251001`, `"sonnet"` → `claude-sonnet-4-6`

**Response `202 Accepted`:**
```json
{"job_id": "arq:job:uuid", "estimated_credits": 20}
```

---

### `GET /v1/metadoc/stream/{job_id}`
SSE stream for Meta-Document generation (text tokens).

**Response:** `text/event-stream`
```
data: {"type": "token", "content": "# Senior Full-Stack Engineer\n\n"}
data: {"type": "token", "content": "## Experience\n\n"}
data: {"type": "done", "doc_id": "uuid", "credits_consumed": 18}
```

---

### `GET /v1/metadoc`
List all generated Meta-Documents.

**Response:** `PaginatedResponse[MetaDocSummary]`

---

### `GET /v1/metadoc/{doc_id}`
Get full Meta-Document content.

**Response:**
```json
{
  "id": "uuid",
  "title": "Resume — Senior Next.js Engineer",
  "original_prompt": "string",
  "content_markdown": "string",
  "contributing_memory_count": 24,
  "generated_at": "ISO8601"
}
```

---

---

## Chat Endpoints (`/v1/chat`)

### `POST /v1/chat/message`
Send a message to the conversational memory chat. Streams response via SSE.

> **Note:** This endpoint uses direct SSE streaming (NOT ARQ). Chat is interactive
> and must return the first token within 3 seconds. Do not route through the job queue.

**Request:**
```json
{
  "message": "string (required)",
  "session_id": "uuid (optional — omit to auto-create a new session)",
  "profile_id": "uuid (optional — scopes retrieval to a System Profile)",
  "model": "haiku | sonnet (optional — defaults to user's preferred_model setting)"
}
```

> If `model` is omitted, the user's `preferred_model` setting is used.
> Valid values: `"haiku"` → `claude-haiku-4-5-20251001`, `"sonnet"` → `claude-sonnet-4-6`

**Response:** `text/event-stream`
```
data: {"type": "session", "session_id": "uuid"}
data: {"type": "token", "content": "Based on your memories..."}
data: {"type": "done", "citations": [{"memory_id": "uuid", "content_preview": "...", "source_filename": "resume.pdf"}], "credits_consumed": 3}
data: {"type": "error", "message": "Response timed out"}
```

**Auth:** `Authorization: Bearer {clerk_jwt}`
**Credits:** 3 (Haiku) | 8 (Sonnet) — checked before retrieval; `402` if insufficient.

---

### `GET /v1/chat/sessions`
List all chat sessions for the current user.

**Query params:** `page`, `page_size`

**Response `200`:** `PaginatedResponse[ChatSessionSummary]`
```json
{
  "items": [{
    "id": "uuid",
    "title": "What ML projects have I worked on?",
    "message_count": 4,
    "profile_id": "uuid",
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }],
  "total": 12,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

---

### `GET /v1/chat/sessions/{session_id}`
Get a full chat session with all messages.

**Response `200`:**
```json
{
  "id": "uuid",
  "title": "string",
  "messages": [
    {"role": "user", "content": "What ML projects...", "created_at": "ISO8601"},
    {"role": "assistant", "content": "Based on your memories...", "created_at": "ISO8601"}
  ],
  "profile_id": "uuid",
  "created_at": "ISO8601"
}
```

---

### `DELETE /v1/chat/sessions/{session_id}`
Delete a chat session (tenant-scoped — user can only delete own sessions).

**Response `200`:** `{"deleted": true}`
**Response `403`:** If session belongs to a different user.

---

## Admin Endpoints (`/v1/admin/`)

All admin endpoints require the `require_admin` FastAPI dependency, which checks that
the authenticated user's Clerk ID is in `settings.admin_user_ids` (from env var
`ADMIN_USER_IDS`). Returns `403` for non-admin authenticated users.

### `GET /v1/admin/users`
Paginated user list with optional search.

**Query params:** `search` (email prefix), `page` (default 1), `limit` (default 20, max 100)

**Response `200`:**
```json
{
  "users": [
    {"id": "uuid", "email": "...", "tier": "free|pro|team",
     "credits_balance": 500, "is_active": true, "created_at": "..."}
  ],
  "total": 1234,
  "page": 1
}
```

### `GET /v1/admin/users/{user_id}`
Full user detail with recent transactions.

**Response `200`:**
```json
{
  "user": {"id": "...", "email": "...", "tier": "...", "credits_balance": 500, "is_active": true},
  "recent_transactions": [
    {"type": "metadoc_haiku", "amount": -18, "created_at": "...", "description": "..."}
  ],
  "source_count": 12,
  "referral_code": "550E8400"
}
```

### `POST /v1/admin/credits/adjust`
Manually adjust a user's credit balance.

**Request:**
```json
{"user_id": "uuid", "amount": 200, "reason": "Support ticket #1234 — payment processed but credits not awarded"}
```

`amount` can be positive (add credits) or negative (remove credits).
Creates a `CreditTransaction` with `type="admin_adjustment"` for audit trail.

**Response `200`:**
```json
{"new_balance": 700, "transaction_id": "uuid"}
```

### `POST /v1/admin/users/{user_id}/toggle-active`
Ban or unban a user account.

**Request:** `{"active": false}` to ban, `{"active": true}` to unban.

**Response `200`:** `{"is_active": false}`

> Sets `User.is_active`. Inactive users get `403` on all authenticated endpoints.
> Does not revoke Clerk session — user can still log in but all API calls fail.

### `GET /v1/admin/stats`
Platform-level metrics for the admin dashboard.

**Response `200`:**
```json
{
  "total_users": 1234,
  "active_today": 89,
  "new_today": 12,
  "pro_users": 78,
  "daily_llm_spend_usd": 12.50,
  "llm_spend_cap_usd": 200.00,
  "sources_today": 45,
  "metadocs_today": 23
}
```

`daily_llm_spend_usd` reads from the Redis circuit breaker key `llm:daily_spend:{today}`.

---

### `PATCH /v1/account/notification-preferences`
Update the user's email notification preferences.

**Request:**
```json
{
  "notify_welcome": true,
  "notify_low_credits": true,
  "notify_ingestion_complete": false
}
```
All fields are optional — send only the fields you want to change (PATCH semantics).

**Response `200`:**
```json
{
  "notify_welcome": true,
  "notify_low_credits": true,
  "notify_ingestion_complete": false
}
```

**Response `422`:** If any value is not a boolean.

> This endpoint updates the `notify_*` boolean columns on the `User` model.
> Changes take effect on the next email trigger. No retroactive action.

---

### `POST /v1/account/apply-referral`
Links a referral code to a new user account. Called from frontend after Clerk signup, before onboarding.

**Request:** `{"referral_code": "550E8400"}`

**Response `200`:** `{"applied": true, "bonus_credits": 200}` if code was valid and applied.
**Response `200`:** `{"applied": false}` if code was invalid, expired, or self-referral — never an error.

> Rate limit: 1 successful application per account. Subsequent calls are no-ops.
> The referral code is case-insensitive (normalized to uppercase before lookup).

---

### `GET /v1/account/referral`
Returns user's referral code, URL, and program stats.

**Response `200`:**
```json
{
  "referral_code": "550E8400",
  "referral_url": "https://ravenbase.app/register?ref=550E8400",
  "total_referrals": 3,
  "pending_referrals": 1,
  "credits_earned": 400
}
```

---

### `POST /v1/account/export`
Triggers background data export. Returns immediately.

**Rate limit:** 1 export request per 24 hours per user.

**Response `202`:**
```json
{"job_id": "uuid", "estimated_minutes": 5,
 "message": "Export preparing. You'll receive an email with a download link."}
```

**Response `429`:** `{"retry_after_seconds": N}` if already requested in last 24 hours.

**Export ZIP contents:**
- `sources/` — original uploaded files
- `meta_documents/` — all Meta-Documents as `.md` files
- `graph_export.json` — Neo4j nodes + edges as JSON
- `profiles.json` — System Profiles config
- `README.txt` — guide to the exported data

**Download:** Pre-signed Supabase Storage URL with 72-hour expiry, delivered via email.

---

### `GET /v1/account/export/status`
Returns status and download URL of most recent export.

**Response `200`:**
```json
{"status": "completed|processing|none", "download_url": "...", "expires_at": "..."}
```

---

### `PATCH /v1/account/model-preference`
Update the user's preferred model for generation tasks.

**Request:**
```json
{ "model": "haiku | sonnet" }
```

**Response `200`:**
```json
{ "preferred_model": "claude-haiku-4-5-20251001" }
```

**Response `422`:** If model is not one of the two valid values.

---

## Webhook Endpoints

### `POST /webhooks/stripe`
Handles Stripe payment events. Validates signature via `stripe.Webhook.construct_event()`.

> **Idempotency:** This endpoint checks `stripe:event:{event_id}` in Redis before
> processing. Duplicate events return `200 {"status":"already_processed"}` immediately.
> Event ID stored with 24h TTL only after successful DB write.
> See STORY-022 AC-11, AC-12.

### `POST /webhooks/resend`
Handles Resend email delivery events.

**Authentication:** Svix webhook signature (`RESEND_WEBHOOK_SECRET` env var).

**Events handled:**
- `email.bounced` — disables relevant `notify_*` flag for recipient user
- `email.complained` — disables ALL `notify_*` flags (spam complaint)

**Response `200`:** `{"status": "handled" | "user_not_found" | "ignored"}`
> Never returns 5xx for missing users — Resend retries 5xx responses, creating infinite loops.

---

## Graph Query Endpoint (`/v1/graph/query`)

### `POST /v1/graph/query`
Convert a natural language question into a Cypher query and execute against the user's knowledge graph.

**Request:**
```json
{
  "query": "Show my Python projects from 2023",
  "profile_id": "uuid (optional)",
  "limit": 20
}
```

**Response `200`:**
```json
{
  "cypher": "MATCH (m:Memory) WHERE m.tenant_id = '...' AND ...",
  "results": {
    "nodes": [{"id": "uuid", "label": "FastAPI project", "type": "memory", "properties": {}}],
    "edges": []
  },
  "explanation": "Found 4 memory nodes matching your query.",
  "query_time_ms": 42
}
```

**Response `422`:** If generated Cypher contains write operations (`CREATE`, `MERGE`, `SET`, `DELETE`, etc.)
```json
{"detail": {"code": "UNSAFE_QUERY", "message": "Query must be read-only"}}
```

**Credits:** 2 per query; `402` if insufficient.

---

## Import Prompt Endpoint (`/v1/ingest/import-prompt`)

### `GET /v1/ingest/import-prompt`
Return a personalized extraction prompt for the user to run in an external AI chat,
then paste the response back for ingestion.

**Query params:** `profile_id` (optional — scopes concept personalization to a profile)

**Response `200`:**
```json
{
  "prompt_text": "Please analyze this conversation and extract a structured knowledge summary.\n\nFocus especially on these topics...",
  "detected_concepts": ["Python", "FastAPI", "TypeScript", "Neo4j"]
}
```

> If the user has no concepts yet (new account), `detected_concepts` is `[]` and
> `prompt_text` contains a generic extraction prompt. Never returns `404`.

---

## Health Endpoint (`/health`)

No auth required.

**Response `200` (healthy):**
```json
{
  "status": "healthy",
  "checks": {
    "postgresql": "ok",
    "redis": "ok",
    "qdrant": "ok",
    "neo4j": "ok"
  },
  "version": "1.0.0"
}
```

**Response `503` (degraded):**
```json
{
  "status": "degraded",
  "checks": {
    "postgresql": "ok",
    "redis": "ok",
    "qdrant": "ERROR: connection refused",
    "neo4j": "ok"
  }
}
```
