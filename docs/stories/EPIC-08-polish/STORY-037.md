# STORY-037: Cold Data Lifecycle — Inactivity Archival

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-024 (GDPR deletion cascade — same multi-store delete pattern), STORY-032 (email service — warning email delivery)

---

> **Before You Start — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (3-layer, ARQ, structlog, lazy imports)
> 2. `docs/architecture/02-database-schema.md` — User model (`last_active_at`, `is_archived`, `notify_account_deletion`, `DataRetentionLog` table)
> 3. `docs/architecture/04-background-jobs.md` — CRON jobs section (WorkerSettings `cron_jobs` pattern)
> 4. `docs/stories/EPIC-08-polish/STORY-024.md` — GDPR deletion cascade (reuse this pattern for the purge phase)
> 5. `docs/stories/EPIC-08-polish/STORY-032.md` — email service (non-fatal, lazy import pattern)

---

## User Story
As the founder, I want inactive Free-tier users' data automatically purged after 180 days
so that Supabase Storage, Qdrant, and Neo4j costs don't bloat indefinitely from abandoned accounts.
As an inactive Free-tier user, I want to receive a 30-day warning before my data is purged
so I can log back in and keep my knowledge graph if I want it.

## Context
- **Who is affected:** Free-tier users ONLY. Pro and Team users are NEVER touched regardless of inactivity.
- **Who is exempt:** Any user with `User.tier IN ('pro', 'team')` OR whose Clerk ID is in `settings.admin_user_ids`.
- **What is purged:** Storage files, Qdrant vectors, Neo4j nodes — identical to the GDPR cascade in STORY-024.
- **What is KEPT:** The PostgreSQL `User` record, the Clerk identity, and the `DataRetentionLog` entry. The user can still log in on day 181 and re-upload their files.
- **Schedule:** ARQ CRON job, every Sunday at 02:00 UTC.

## Acceptance Criteria

### Activity Tracking
- [ ] AC-1: FastAPI middleware updates `User.last_active_at = now()` on every authenticated request, debounced to at most once per calendar day per user (check `last_active_at.date() == today` before writing)
- [ ] AC-2: `last_active_at` is set to `created_at` value on user creation (so new users don't immediately qualify for archival)
- [ ] AC-3: Middleware never updates `last_active_at` for unauthenticated requests or health-check endpoints

### CRON Task — Phase 1: Warning (Day 150)
- [ ] AC-4: `cleanup_cold_data` ARQ task runs every Sunday at 02:00 UTC via `cron_jobs` in `WorkerSettings`
- [ ] AC-5: Phase 1 query: `User.tier == 'free' AND last_active_at < NOW() - INTERVAL '150 days' AND is_archived == False AND notify_account_deletion == True`
- [ ] AC-6: For each matching user: send warning email via `EmailService` with subject "Your Ravenbase data will be archived in 30 days" and a "Keep my data" CTA linking to `/dashboard` (logs user in and resets `last_active_at`)
- [ ] AC-7: Email send is non-fatal — log error and continue if Resend fails (never abort the batch)
- [ ] AC-8: `DataRetentionLog` record created with `event_type="warning_sent"`, `days_inactive=N`

### CRON Task — Phase 2: Purge (Day 180)
- [ ] AC-9: Phase 2 query: `User.tier == 'free' AND last_active_at < NOW() - INTERVAL '180 days' AND is_archived == False`
- [ ] AC-10: Exemption check: skip any user whose Clerk ID is in `settings.admin_user_ids` — log `cold_data.skip_admin` and continue
- [ ] AC-11: Purge executes the same cascade as STORY-024: Supabase Storage → Qdrant vectors → Neo4j nodes + edges (in that order)
- [ ] AC-12: After purge: set `User.is_archived = True`, set `User.credits_balance = 0` — do NOT delete the `User` row or the Clerk identity
- [ ] AC-13: `DataRetentionLog` record created with `event_type="data_purged"`, `days_inactive=N`, `sources_deleted`, `qdrant_vectors_deleted`, `neo4j_nodes_deleted`, `storage_bytes_freed`
- [ ] AC-14: If any purge step fails for a user: log `cold_data.purge_step_failed`, skip that user for this run (retry next Sunday), do NOT set `is_archived = True`

### Safeguards
- [ ] AC-15: Task processes users in batches of 50 (never load all inactive users into memory at once)
- [ ] AC-16: Total runtime logged: `cold_data.run_complete` with `warnings_sent`, `purges_executed`, `errors`, `duration_ms`
- [ ] AC-17: If user logs back in after warning but before purge: `last_active_at` update (AC-1) automatically resets the 180-day clock — no special logic needed

### Frontend — Archived State
- [ ] AC-18: If authenticated user has `User.is_archived == True`: API returns `User` object with `is_archived: true` in `GET /v1/users/me` response
- [ ] AC-19: Dashboard detects `is_archived == true` and renders the State 2 "No Memories Yet" empty state with additional copy: "Your previous data was archived after 180 days of inactivity. Upload files to rebuild your knowledge graph." — same as a new user

## Technical Notes

### Files to Create (Backend)
- `src/workers/tasks/cold_data.py` — `cleanup_cold_data` ARQ task

### Files to Modify (Backend)
- `src/api/middleware/activity.py` — new file: `ActivityTrackingMiddleware`
- `src/api/main.py` — register `ActivityTrackingMiddleware`
- `src/workers/main.py` — add `cleanup_cold_data` to `functions` + `cron_jobs`

### Activity Middleware Pattern

```python
# src/api/middleware/activity.py
from datetime import date, datetime, UTC
from starlette.middleware.base import BaseHTTPMiddleware

SKIP_PATHS = {"/health", "/metrics", "/webhooks/clerk", "/webhooks/stripe",
              "/webhooks/resend", "/v1/ingest/stream"}  # SSE is high-frequency

class ActivityTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Only track authenticated API requests, skip noise
        user_id = getattr(request.state, "user_id", None)
        if not user_id or request.url.path in SKIP_PATHS:
            return response

        # Debounce: write at most once per day per user
        # Use a Redis key to avoid hitting PostgreSQL on every request
        redis = request.app.state.redis
        cache_key = f"activity:{user_id}:{date.today().isoformat()}"
        if not await redis.exists(cache_key):
            await redis.setex(cache_key, 86400, "1")  # Expires in 24h
            # Fire-and-forget DB update (don't await — never slow down the request)
            import asyncio  # noqa: PLC0415
            asyncio.create_task(_update_last_active(user_id, request.app.state.db_pool))

        return response

async def _update_last_active(user_id: str, db_pool) -> None:
    """Background task — update last_active_at without blocking the response."""
    try:
        async with db_pool() as db:
            user = await db.get(User, user_id)
            if user:
                user.last_active_at = datetime.now(UTC)
                await db.commit()
    except Exception as e:
        log.warning("activity.update_failed", user_id=user_id, error=str(e))
```

### Cold Data Task Pattern

```python
# src/workers/tasks/cold_data.py
from datetime import datetime, UTC, timedelta
from structlog import get_logger
from src.services.deletion_service import DeletionService  # Reuse STORY-024

log = get_logger()

WARNING_THRESHOLD_DAYS = 150
PURGE_THRESHOLD_DAYS = 180
BATCH_SIZE = 50

async def cleanup_cold_data(ctx: dict) -> dict:
    """
    Phase 1 (day 150): Send warning email to inactive Free users.
    Phase 2 (day 180): Purge storage data, set is_archived=True.

    Never touches Pro, Team, or admin users.
    Processes in batches of 50 to avoid memory spikes.
    """
    db = ctx["db"]
    redis = ctx["redis"]
    now = datetime.now(UTC)

    stats = {"warnings_sent": 0, "purges_executed": 0, "errors": 0}
    start = now

    # ── Phase 1: Warning ─────────────────────────────────────────────────────
    warning_cutoff = now - timedelta(days=WARNING_THRESHOLD_DAYS)
    warning_users = await _get_inactive_free_users(
        db, before=warning_cutoff, is_archived=False, notify_deletion=True
    )

    for user in warning_users:
        try:
            await email_service.send_inactivity_warning(user.email, user.display_name)
            await db.add(DataRetentionLog(
                user_id=user.id, event_type="warning_sent",
                days_inactive=(now - user.last_active_at).days,
            ))
            await db.commit()
            stats["warnings_sent"] += 1
        except Exception as e:
            log.error("cold_data.warning_failed", user_id=str(user.id), error=str(e))
            stats["errors"] += 1

    # ── Phase 2: Purge ───────────────────────────────────────────────────────
    purge_cutoff = now - timedelta(days=PURGE_THRESHOLD_DAYS)
    purge_users = await _get_inactive_free_users(
        db, before=purge_cutoff, is_archived=False, notify_deletion=None
    )

    admin_ids = {uid.strip() for uid in settings.ADMIN_USER_IDS.split(",") if uid.strip()}

    for user in purge_users:
        # Exemption: skip admin users regardless of tier
        if str(user.clerk_id) in admin_ids:
            log.info("cold_data.skip_admin", user_id=str(user.id))
            continue

        try:
            # Reuse STORY-024 deletion service (same cascade, same order)
            result = await DeletionService.purge_tenant_data(
                tenant_id=str(user.id), db=db, redis=redis
            )
            user.is_archived = True
            user.credits_balance = 0
            await db.add(DataRetentionLog(
                user_id=user.id, event_type="data_purged",
                days_inactive=(now - user.last_active_at).days,
                sources_deleted=result.sources_deleted,
                qdrant_vectors_deleted=result.vectors_deleted,
                neo4j_nodes_deleted=result.graph_nodes_deleted,
                storage_bytes_freed=result.bytes_freed,
            ))
            await db.commit()
            stats["purges_executed"] += 1
        except Exception as e:
            log.error("cold_data.purge_failed", user_id=str(user.id), error=str(e))
            stats["errors"] += 1
            await db.rollback()  # Don't partially archive

    duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
    log.info("cold_data.run_complete", duration_ms=duration_ms, **stats)
    return stats
```

### Architecture Constraints
- **Never delete Pro or Team users' data** — the query explicitly filters `tier == 'free'`
- **Never delete admin users' data** — exempt check uses `settings.admin_user_ids`
- **Never delete the User PostgreSQL row or Clerk identity** — only set `is_archived=True`
- **Reuse `DeletionService` from STORY-024** — don't duplicate the cascade logic
- **Fire-and-forget activity updates** — middleware uses `asyncio.create_task()`, never awaits
- **Redis debounce key** — prevents PostgreSQL write on every API request (TTL matches 1 day)
- **Batch size 50** — prevents loading thousands of inactive users into memory at once

## Definition of Done
- [ ] `ActivityTrackingMiddleware` updates `last_active_at` (debounced via Redis, once/day)
- [ ] CRON task runs Sunday 02:00 UTC via `WorkerSettings.cron_jobs`
- [ ] Phase 1: warning email sent + `DataRetentionLog` record at day 150
- [ ] Phase 2: storage purged + `User.is_archived=True` + log at day 180
- [ ] Pro/Team/admin users never touched (tested explicitly)
- [ ] Archived user can still log in and sees "re-upload" empty state
- [ ] `make quality && make test` passes

## Testing This Story

```bash
# Unit tests:
# 1. Test exemption logic: user with pro tier → assert NOT purged
# 2. Test exemption logic: user ID in ADMIN_USER_IDS → assert NOT purged
# 3. Test debounce: call middleware twice same day → assert DB write called once
# 4. Test phase threshold: user inactive 149 days → warning NOT sent
#    user inactive 150 days → warning sent
#    user inactive 179 days → purge NOT executed
#    user inactive 180 days → purge executed

# Integration test:
# 1. Create Free user, set last_active_at = NOW() - 181 days
# 2. Run cleanup_cold_data task manually
# 3. Assert User.is_archived == True
# 4. Assert User.credits_balance == 0
# 5. Assert User record still exists in PostgreSQL
# 6. Assert Qdrant vectors for this tenant = 0
# 7. Assert DataRetentionLog row created with event_type="data_purged"
# 8. Assert user can still authenticate (Clerk identity untouched)
```

---

## Agent Implementation Brief

```
Implement STORY-037: Cold Data Lifecycle — Inactivity Archival.

Read first:
1. CLAUDE.md (architecture rules — 3-layer, ARQ, lazy imports, structlog)
2. docs/architecture/02-database-schema.md (User new fields + DataRetentionLog table)
3. docs/architecture/04-background-jobs.md (CRON jobs section — WorkerSettings pattern)
4. docs/stories/EPIC-08-polish/STORY-024.md (GDPR deletion cascade — reuse DeletionService)
5. docs/stories/EPIC-08-polish/STORY-032.md (email non-fatal pattern)
6. docs/stories/EPIC-08-polish/STORY-037.md (this file)

Key constraints:
- NEVER delete Pro/Team users' data — query must filter tier == 'free'
- NEVER delete admin users — check settings.admin_user_ids before purge
- NEVER delete PostgreSQL User row or Clerk identity — only set is_archived=True
- Reuse DeletionService from STORY-024, do not duplicate cascade logic
- Activity middleware uses asyncio.create_task() — never await (never slow requests)

Show plan first. Do not implement yet.
```

## Development Loop
Follow `docs/DEVELOPMENT_LOOP.md`.
```bash
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-037 cold data lifecycle and inactivity archival"
git push
# Update epics.md: 🔲 → ✅ for STORY-037
```
