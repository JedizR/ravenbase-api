# STORY-002: PostgreSQL Schema + Alembic Migrations

**Epic:** EPIC-01 — Foundation Infrastructure
**Priority:** P0
**Complexity:** Medium
**Depends on:** STORY-001
**Type:** Backend
**Repo:** ravenbase-api

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — database schema and Alembic migrations story.

## Component
Infrastructure

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 4: schemas first)
> 2. `docs/architecture/02-database-schema.md` — all SQLModel table definitions (copy exactly)
> 3. `docs/development/02-coding-standards.md` — configuration pattern, `pydantic-settings` usage
> 4. `docs/architecture/01-tech-stack-decisions.md` — ADR-005 (SQLModel), ADR-006 (Alembic)

---

## User Story
As a developer, I want all database tables created via Alembic migrations so that the schema is version-controlled and rollback is possible.

## Context
- DB models: `architecture/02-database-schema.md` — all SQLModel classes
- Service pattern: `development/02-coding-standards.md`
- Never use `create_all()` — always Alembic

## Acceptance Criteria
- [ ] AC-1: All 7 SQLModel table classes exist in `src/models/`: `User`, `SystemProfile`, `Source`, `SourceAuthorityWeight`, `Conflict`, `MetaDocument`, `CreditTransaction`, `JobStatus`
- [ ] AC-2: Alembic `env.py` is configured to auto-detect SQLModel models
- [ ] AC-3: `uv run alembic upgrade head` creates all tables without errors
- [ ] AC-4: `uv run alembic downgrade -1` cleanly removes the last migration
- [ ] AC-5: `pydantic-settings` config loads all required env vars; app fails loudly with clear error if any required var is missing
- [ ] AC-6: `get_db` async session dependency is implemented in `src/api/dependencies/db.py`
- [ ] AC-7: All tables have correct indexes: `idx_sources_user_id`, `idx_conflicts_user_id_status`, `idx_job_statuses_user_id`

## Technical Notes

### Files to Create
- `src/models/user.py` — User model
- `src/models/profile.py` — SystemProfile model
- `src/models/source.py` — Source model + SourceAuthorityWeight + SourceStatus constants
- `src/models/conflict.py` — Conflict model + ConflictStatus constants
- `src/models/meta_document.py` — MetaDocument model
- `src/models/credit.py` — CreditTransaction model
- `src/models/job_status.py` — JobStatus model
- `alembic/versions/001_initial_schema.py` — auto-generated migration

### Files to Modify
- `alembic/env.py` — import all models for autogenerate
- `src/core/config.py` — add all settings fields

### Architecture Constraints
- Every model must include `tenant_id` / `user_id` (UUID)
- Timestamps must use `datetime.now(UTC)` — not `datetime.utcnow()` (deprecated)
- Alembic migration file must be committed, not just the models

## Definition of Done
- [ ] `make db-upgrade` runs cleanly on fresh database
- [ ] `make quality` passes (0 errors)
- [ ] Integration test: `test_database_connectivity` passes

## Testing This Story

```bash
# Apply migrations:
uv run alembic upgrade head
# Expected: No errors. All tables created.

# Verify tables exist:
docker exec -it ravenbase_postgres psql -U dev -d ravenbase_dev \
  -c "\dt"
# Expected: users, system_profiles, sources, source_authority_weights,
#           conflicts, meta_documents, credit_transactions, job_statuses

# Test rollback:
uv run alembic downgrade -1
# Expected: Clean rollback with no errors

# Re-apply:
uv run alembic upgrade head

# Quality:
make quality
```

**Passing result:** All 8 tables created. `alembic downgrade -1` works cleanly. `make quality` passes.

---

## Agent Implementation Brief

```
Implement STORY-002: PostgreSQL Schema + Alembic Migrations.

Read first:
1. CLAUDE.md (architecture rules — RULE 4: write models FIRST)
2. docs/architecture/02-database-schema.md (copy the SQLModel class definitions exactly)
3. docs/development/02-coding-standards.md (Settings class with pydantic-settings)
4. docs/stories/EPIC-01-foundation/STORY-002.md (this file)

Key constraints:
- NEVER use SQLModel.metadata.create_all() — always Alembic
- Timestamps must use datetime.now(UTC) not datetime.utcnow() (deprecated)
- Every model needs user_id/tenant_id UUID field with index=True
- Commit the generated alembic/versions/ migration file
- Settings required fields use Field(...) — app fails loudly if missing

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
git add -A && git commit -m "feat(ravenbase): STORY-002 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-002"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-002
git add docs/stories/epics.md && git commit -m "docs: mark STORY-002 complete"
```
