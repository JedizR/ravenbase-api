# STORY-035: Data Export / Right to Portability

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-024 (same multi-store pattern), STORY-032 (email service)

---

> **Before You Start — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (3-layer, ARQ, structlog)
> 2. `docs/architecture/02-database-schema.md` — all models being exported
> 3. `docs/stories/EPIC-08-polish/STORY-024.md` — GDPR deletion (same multi-store approach)
> 4. `docs/stories/EPIC-08-polish/STORY-032.md` — email service (send completion email)

---

## User Story
As a user, I want to download all my Ravenbase data in a portable format so I can
take my knowledge graph elsewhere or simply have a backup.

## Context
- GDPR Article 20 (Right to Data Portability) for EU users
- Export is async ARQ job — files can be very large
- Completion notification via Resend email
- Download link = pre-signed Supabase Storage URL (72-hour expiry)
- Rate limited: 1 export per 24 hours per user

## Acceptance Criteria
- [ ] AC-1: `POST /v1/account/export` returns `202` with `job_id` and enqueues ARQ task
- [ ] AC-2: Rate limit: second request within 24h returns `429` with `retry_after_seconds`
- [ ] AC-3: ARQ task collects: original source files, Meta-Documents as `.md`, Neo4j graph as JSON, SystemProfiles as JSON
- [ ] AC-4: All files compressed into ZIP at `exports/{user_id}/{timestamp}.zip` in Supabase Storage
- [ ] AC-5: Pre-signed download URL generated (72-hour expiry)
- [ ] AC-6: Completion email sent via `EmailService` with download link (respects `notify_ingestion_complete` preference)
- [ ] AC-7: `GET /v1/account/export/status` returns current status and URL
- [ ] AC-8: Settings → Data page has "Export my data" button + "last exported" timestamp
- [ ] AC-9: If any single component fails (e.g. Neo4j export errors): log error, skip that component, complete ZIP with `PARTIAL_EXPORT.txt` explaining what was excluded — never fail the whole job
- [ ] AC-10: Export ZIPs auto-deleted from Supabase Storage after 7 days

## Technical Notes

### Files to Create
- `src/workers/tasks/export.py` — `generate_user_export` ARQ task
- `src/services/export_service.py`

### Architecture Constraints
- Filter ALL queries by `tenant_id` — never include other users' data
- Never include raw Qdrant vectors (derived data, not user data per GDPR)
- Partial failures are non-fatal — produce `PARTIAL_EXPORT.txt` not a failed job
- Rate limit via Redis key `export:cooldown:{user_id}` TTL 24h
- Store only `storage_path` in JobStatus (URL is ephemeral, regenerated on status check)
- Export idempotency: if ZIP already exists at `storage_path`, skip recreation (for ARQ retries)

## Definition of Done
- [ ] `POST /v1/account/export` returns 202 with job_id
- [ ] ZIP created in Supabase Storage with all 4 components
- [ ] Partial failures produce PARTIAL_EXPORT.txt (job does not fail)
- [ ] Email sent with download link
- [ ] Rate limit enforced (24h cooldown)
- [ ] `make quality && make test` passes

## Testing This Story

```bash
# Test data export flow end-to-end:
# 1. POST /v1/account/export → expect 202 with job_id
# 2. Poll GET /v1/account/export/status until status = "completed"
# 3. Verify download_url is a Supabase pre-signed URL (contains "supabase.co")
# 4. Download the ZIP and verify it contains:
#    - sources/ directory (original uploaded files)
#    - meta_documents/ directory (.md files)
#    - graph_export.json
#    - profiles.json
#    - README.txt
# 5. POST /v1/account/export again immediately → expect 429 with retry_after_seconds
# 6. Verify export ZIP contains ONLY this user's data (check no other tenant_id present)
# 7. Partial failure test: mock Neo4j adapter to raise an exception → verify job still
#    completes with PARTIAL_EXPORT.txt listing "Knowledge Graph: <error message>"
# 8. Verify download_url expires after 72 hours (check Supabase signed URL expiry param)
```

## Agent Implementation Brief

```
Implement STORY-035: Data Export / Right to Portability.

Read first:
1. CLAUDE.md
2. docs/architecture/02-database-schema.md
3. docs/stories/EPIC-08-polish/STORY-024.md (same multi-store delete → export pattern)
4. docs/stories/EPIC-08-polish/STORY-032.md (email for completion notification)
5. docs/stories/EPIC-08-polish/STORY-035.md (this file)

Key: Partial failures are non-fatal. Never include vectors. Filter by tenant_id everywhere.
Show plan first.
```

## Development Loop
Follow `docs/DEVELOPMENT_LOOP.md`.
```bash
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-035 data export and portability"
```
