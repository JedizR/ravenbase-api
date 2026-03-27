# STORY-024: GDPR Account Deletion Cascade

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium
**Depends on:** All data stories (STORY-001 through STORY-023)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-11-AC-1: DELETE /v1/account triggers cascade deletion across PostgreSQL, Qdrant, Neo4j, and Supabase Storage
- FR-11-AC-2: Deletion completes within 60 seconds for typical accounts

## Component
COMP-07: PrivacyLayer

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/architecture/05-security-privacy.md` — GDPR deletion spec, cascade order, audit logging
> 3. `docs/architecture/02-database-schema.md` — all tables that must be purged
> 4. `docs/architecture/04-background-jobs.md` — `cascade_delete_source` task pattern
> 5. `docs/prd/04-non-functional-requirements.md` — 60-second SLA requirement

---

## User Story
As a user, I want to permanently delete my account and all associated data so that I control my digital footprint.

## Context
- Security/GDPR spec: `architecture/05-security-privacy.md` — full cascade order and audit requirements
- Database schema: `architecture/02-database-schema.md` — all tables to delete from
- Background jobs: `architecture/04-background-jobs.md` — use `cascade_delete_source` pattern
- Non-functional requirements: `prd/04-non-functional-requirements.md` — 60-second SLA

## Acceptance Criteria
- [ ] AC-1: `DELETE /v1/account` endpoint triggers full deletion cascade (enqueues ARQ job, returns 202)
- [ ] AC-2: Cascade order: Supabase Storage files → Qdrant vectors → Neo4j nodes+edges → PostgreSQL (all tables) → Clerk account
- [ ] AC-3: Each step logged to structlog with `action=gdpr_deletion`, `step=storage|qdrant|neo4j|postgres|clerk`, `user_id=Y`
- [ ] AC-4: Full cascade completes within 60 seconds (SLA from `prd/04-non-functional-requirements.md`)
- [ ] AC-5: Integration test confirms zero data remains after deletion in all 4 data stores
- [ ] AC-6: Frontend: "Delete Account" button in Settings with AlertDialog confirmation ("Type DELETE to confirm")
- [ ] AC-7: Post-deletion: Clerk session invalidated, redirect to `/` with "Account deleted" toast
- [ ] AC-8: If any step fails: log the error, continue cascade (don't abort — partial deletion is better than no deletion)
- [ ] AC-9: Audit trail: structured log entry with timestamps for each deletion step stored persistently (before PostgreSQL delete)

## Technical Notes

### Files to Create
- `src/workers/deletion_tasks.py` — `cascade_delete_account` ARQ task (separate from `cascade_delete_source`)
- `src/services/deletion_service.py` — `delete_account()` method that calls each adapter in order
- `src/api/routes/account.py` — `DELETE /v1/account` endpoint
- `tests/integration/api/test_gdpr_deletion.py` — end-to-end cascade test

### Files to Modify
- `src/workers/main.py` — add `cascade_delete_account` to WorkerSettings.functions
- `src/api/main.py` — include `account` router

### Architecture Constraints
- The `DELETE /v1/account` route MUST enqueue an ARQ job and return 202 immediately — the cascade takes up to 60s
- Cascade MUST run in this order (never reverse): Storage → Qdrant → Neo4j → PostgreSQL → Clerk
- PostgreSQL deletion order: `job_statuses`, `credit_transactions`, `meta_documents`, `conflicts`, `source_authority_weights`, `sources`, `system_profiles`, `users`
- Clerk account deletion uses Clerk API: `clerk.users.delete_user(user_id)`
- Qdrant deletion: `qdrant_adapter.delete_by_filter(Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=user_id))]))`
- Neo4j deletion: `MATCH (n {tenant_id: $tenant_id}) DETACH DELETE n`
- NEVER delete without verifying `user_id` from JWT — this is irreversible

### Deletion Task Pattern
```python
# src/workers/deletion_tasks.py
async def cascade_delete_account(ctx: Ctx, *, user_id: str) -> dict:
    log = logger.bind(tenant_id=user_id, action="gdpr_deletion", job="cascade_delete_account")
    log.info("gdpr_deletion.started")

    service = DeletionService()

    # Step 1: Supabase Storage (all files under /{user_id}/)
    await service.delete_storage_by_tenant(user_id)
    log.info("gdpr_deletion.step_complete", step="storage")

    # Step 2: Qdrant (all vectors where tenant_id = user_id)
    await service.delete_qdrant_by_tenant(user_id)
    log.info("gdpr_deletion.step_complete", step="qdrant")

    # Step 3: Neo4j (all nodes where tenant_id = user_id, DETACH DELETE)
    await service.delete_neo4j_by_tenant(user_id)
    log.info("gdpr_deletion.step_complete", step="neo4j")

    # Step 4: PostgreSQL (all tables in FK-safe order)
    await service.delete_postgres_by_tenant(user_id)
    log.info("gdpr_deletion.step_complete", step="postgres")

    # Step 5: Clerk account
    await service.delete_clerk_user(user_id)
    log.info("gdpr_deletion.step_complete", step="clerk")

    log.info("gdpr_deletion.completed", total_steps=5)
    return {"user_id": user_id, "status": "deleted"}
```

### Frontend Pattern
```tsx
// app/(dashboard)/settings/page.tsx — danger zone section
// Use shadcn AlertDialog for "Type DELETE to confirm"
<AlertDialog>
  <AlertDialogTrigger asChild>
    <Button variant="destructive">Delete Account</Button>
  </AlertDialogTrigger>
  <AlertDialogContent>
    <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
    <AlertDialogDescription>
      This action cannot be undone. All your memories, sources, and graph data will be permanently deleted.
      Type DELETE to confirm.
    </AlertDialogDescription>
    <Input
      value={confirmText}
      onChange={(e) => setConfirmText(e.target.value)}
      placeholder="Type DELETE"
    />
    <AlertDialogAction
      disabled={confirmText !== "DELETE"}
      onClick={handleDeleteAccount}
    >
      Delete my account permanently
    </AlertDialogAction>
  </AlertDialogContent>
</AlertDialog>
```

## Definition of Done
- [ ] `DELETE /v1/account` returns 202 and enqueues cascade job
- [ ] Cascade runs in correct order: Storage → Qdrant → Neo4j → PostgreSQL → Clerk
- [ ] Integration test `test_gdpr_deletion_cascade` passes (all stores empty after cascade)
- [ ] Each step logged with `action=gdpr_deletion` and step name
- [ ] Frontend: Delete dialog with "Type DELETE" confirmation works
- [ ] `make quality` passes (0 errors)
- [ ] `make test` passes

## Testing This Story

```bash
# Run GDPR deletion integration test:
uv run pytest tests/integration/api/test_gdpr_deletion.py -v

# Expected output:
# test_gdpr_deletion_cascade PASSED
# test_gdpr_deletion_requires_auth PASSED
# test_gdpr_deletion_tenant_scoped PASSED
```

**Passing result:** After `DELETE /v1/account`, all 4 data stores return zero records for the test user's `tenant_id`. Clerk user is deleted.

---

## Agent Implementation Brief

```
Implement STORY-024: GDPR Account Deletion Cascade.

Read first:
1. CLAUDE.md (architecture rules — especially RULE 2 tenant isolation and RULE 3 async jobs)
2. docs/architecture/05-security-privacy.md (GDPR section — full cascade spec)
3. docs/architecture/02-database-schema.md (all PostgreSQL tables to delete)
4. docs/architecture/04-background-jobs.md (cascade_delete_source pattern to follow)
5. docs/stories/EPIC-08-polish/STORY-024.md (this file)

Key constraints:
- DELETE /v1/account MUST return 202 and enqueue ARQ job — never run cascade synchronously
- Cascade order is fixed: Storage → Qdrant → Neo4j → PostgreSQL → Clerk
- On partial failure, log and continue — do not abort the cascade
- PostgreSQL tables must be deleted in FK-safe order
- tenant_id MUST come from the JWT (require_user), never from the request body

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
git add -A && git commit -m "feat(ravenbase): STORY-024 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-024"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-024
git add docs/stories/epics.md && git commit -m "docs: mark STORY-024 complete"
```
