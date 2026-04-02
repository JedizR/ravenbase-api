# STORY-042 — Production Deployment

> **Story ID:** STORY-042
> **Epic:** EPIC-10 — Production Launch
> **Type:** DevOps
> **Priority:** P0 — final step
> **Sprint:** 42
> **DEPENDS ON:** STORY-039, STORY-040, STORY-041, all external accounts created

---

## Summary

Deploy `ravenbase-api` to Railway and `ravenbase-web` to Vercel. Configure all external services (Clerk, Qdrant, Neo4j AuraDB, Supabase, Stripe, Resend). Run end-to-end smoke tests to verify the live system.

---

## Prerequisites (user must complete before starting)

All accounts must be created and API keys collected:

- [ ] Railway account — railway.app
- [ ] Vercel account — vercel.com
- [ ] Clerk PRODUCTION application — clerk.com (separate from dev application)
- [ ] Qdrant Cloud cluster — cloud.qdrant.io (free tier)
- [ ] Neo4j AuraDB instance — neo4j.com/cloud/aura (free tier)
- [ ] Supabase project — supabase.com (create bucket "ravenbase-sources")
- [ ] Stripe account (live mode, create 4 Price objects)
- [ ] Resend account — resend.com
- [ ] Anthropic API key
- [ ] OpenAI API key
- [ ] Google AI (Gemini) API key
- [ ] Sentry project (optional but recommended)

---

## Deployment Steps

Follow `docs/components/REFACTOR_PLAN.md PART 6 (Railway)` then `PART 7 (Vercel)` exactly.

**Railway (backend):**
1. Connect GitHub repo → create 2 services (api + worker)
2. Add PostgreSQL + Redis databases
3. Set ~25 environment variables per service
4. Set pre-deploy command: `uv run alembic upgrade head`
5. Set custom domain: `api.ravenbase.app`
6. Configure Stripe + Clerk webhook endpoints

**Vercel (frontend):**
1. Connect GitHub repo
2. Set ~10 environment variables
3. Configure Clerk Production app redirect URLs
4. Deploy → set custom domain: `ravenbase.app`

---

## Cross-references

- `docs/components/REFACTOR_PLAN.md` — PART 6 (Railway), PART 7 (Vercel), PART 8 (env vars), PART 9 (smoke tests)

---

## Acceptance Criteria (all smoke tests from REFACTOR_PLAN.md PART 9 must pass)

**Health:**
- [ ] `https://api.ravenbase.app/health` → `{"status": "healthy", "postgres": "ok", "redis": "ok"}`
- [ ] `https://ravenbase.app` → 200 OK

**Auth flow:**
- [ ] Registration → `/onboarding` → complete → `/chat` (not 404)
- [ ] `/dashboard` → 307 redirect to `/chat`
- [ ] Unauthenticated at `/chat` → redirect to `/login`

**Admin bypass:**
- [ ] Admin user generates Meta-Doc → 0 credits deducted
- [ ] Sidebar shows `◆ ADMIN_ACCESS` for admin user

**Core features:**
- [ ] `/ingest "test"` via Omnibar → captured successfully
- [ ] Upload PDF → source appears as "completed" within 60s
- [ ] Generate Meta-Doc → tokens stream → `◆ SAVED_JUST_NOW`
- [ ] Chat message → response streams → citation cards appear

**Security:**
- [ ] `curl -I https://ravenbase.app` → `X-Frame-Options: DENY` header present
- [ ] Webhook endpoints return 400 (not 404) without valid signature
