# STORY-040 — Admin Bypass System

> **Story ID:** STORY-040
> **Epic:** EPIC-10 — Production Launch
> **Type:** Cross-repo (Backend + Frontend)
> **Priority:** P0 — must complete before LLM feature testing
> **Sprint:** 40
> **DEPENDS ON:** STORY-039 (env setup complete)

---

## Summary

Implement the admin bypass system so that designated admin users (identified by `ADMIN_USER_IDS` env var) can use all LLM features without consuming credits. Without this, admin users get blocked by 402 errors after their initial 500 credits are exhausted, making it impossible to test Meta-Doc generation, Chat, and other paid features.

---

## Work Items

| Item | Repo | File | Description |
|---|---|---|---|
| ADMIN-001 | ravenbase-api | src/services/credit_service.py | Add admin bypass to check_or_raise() and deduct() |
| ADMIN-002 | ravenbase-api | src/api/routes/account.py (or similar) | Add is_admin field to GET /v1/me response |
| ADMIN-003 | ravenbase-web | components/domain/Sidebar.tsx | Show ◆ ADMIN_ACCESS instead of credit count |
| ADMIN-004 | ravenbase-web | app/(marketing)/pricing/page.tsx | Show admin bypass message instead of tier cards |
| BUG-006 | ravenbase-api | src/services/credit_service.py | Same as ADMIN-001 |
| BUG-011 | both repos | .envs/.env.dev / .env.local | Set real Clerk user ID in ADMIN_USER_IDS |

---

## Cross-references

- `docs/components/REFACTOR_PLAN.md` — ADMIN-001 through ADMIN-004 exact code
- `docs/components/BE-COMP-06-CreditSystem.md` — admin bypass specification
- `docs/components/BE-COMP-05-AuthSystem.md` — GET /v1/me is_admin field

---

## How to Get Your Clerk User ID (BUG-011)

1. Go to Clerk Dashboard
2. Click the Production (or Development) application
3. Click "Users" in the left sidebar
4. Click your user account
5. Copy the User ID (format: `user_2abc123...`)
6. Set in `ravenbase-api/.envs/.env.dev`: `ADMIN_USER_IDS=user_2abc123`
7. Set in `ravenbase-web/.env.local`: `ADMIN_USER_IDS=user_2abc123`

---

## Acceptance Criteria

- [ ] `ADMIN_USER_IDS` set to real Clerk user ID in both repos' env files (BUG-011)
- [ ] Admin user generates Meta-Doc → `CreditTransaction` record has `amount=0` and `operation="admin_bypass:meta_doc_haiku"` (ADMIN-001)
- [ ] Admin user sends Chat message → 0 credits deducted (ADMIN-001)
- [ ] Admin user uploads file → 0 credits deducted (ADMIN-001)
- [ ] `GET /v1/me` with admin JWT → `{"is_admin": true}` (ADMIN-002)
- [ ] `GET /v1/me` with regular JWT → `{"is_admin": false}` (ADMIN-002)
- [ ] Sidebar: admin user sees `◆ ADMIN_ACCESS` (not credit count) (ADMIN-003)
- [ ] Pricing page: admin user sees "Admin Account — Full Access Bypass Active" (not tier cards) (ADMIN-004)
- [ ] Backend quality gate: `make quality` → 0 errors
- [ ] Frontend build: `npm run build` → 0 TypeScript errors
