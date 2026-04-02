# Ravenbase — Current Project Status

> **Agent instruction:** Read this file at the start of every session before doing anything else.
> It tells you exactly where the project is right now.

---

## Current State

**Phase:** B — Production Launch
**Current sprint:** 42
**Status:** DEPLOYMENT READY — STORY-039/040/041 complete. All critical bugs fixed, admin bypass implemented, deployment configs created. Next: STORY-042 Production Deployment.

**Next story to implement:** STORY-042 (Production Deployment — Railway + Vercel)
**Story file:** `docs/stories/EPIC-10-production-launch/STORY-042.md`

**State:** All critical bugs fixed. System is code-complete and ready for deployment.
- ✅ BUG-001: Double Header/Footer removed from marketing pages
- ✅ BUG-002: /dashboard → redirects to /chat (app/dashboard/page.tsx)
- ✅ BUG-003: Header backdrop-blur removed (solid bg-background)
- ✅ BUG-004: Authenticated users visiting / redirect to /chat
- ✅ BUG-005: Onboarding completion → /chat (not /dashboard)
- ✅ BUG-009: Dockerfile.api --reload → --workers 2
- ✅ BUG-010: vercel.json created with security headers
- ✅ BUG-013: Nav links now absolute paths (/#how-it-works)
- ✅ BUG-014: Fake testimonials removed
- ✅ BUG-015: Delete Account now calls API (CRITICAL fix)
- ✅ BUG-021: /search and /generate removed from Omnibar
- ✅ BUG-022: MemoryChat reader cancelled on unmount
- ✅ BUG-025: GraphQueryBar example clicks auto-execute
- ✅ BUG-026: Admin progress bar uses CSS custom property
- ✅ BUG-028: MemoryInbox activeIndex clamped to 0
- ✅ BUG-033: Checkout URL validated before redirect
- ✅ ADMIN-001: CreditService admin bypass
- ✅ ADMIN-002: GET /v1/users/me returns is_admin
- ✅ ADMIN-003: Sidebar shows ◆ ADMIN_ACCESS for admin users
- ✅ ADMIN-004: Pricing page shows admin bypass message
- ✅ UX-001: Sources Upload tab wired to IngestionDropzone
- ✅ DEPLOY-001: vercel.json created
- ✅ DEPLOY-002: next.config.mjs updated with image remotePatterns

---

## Last Completed Stories

**STORY-041 (2026-04-02)** — Sources Page Upload + UX Gaps + Deployment Config
**STORY-040 (2026-04-02)** — Admin Bypass System
**STORY-039 (2026-04-02)** — Critical Bug Fixes

---

## Context for Next Session

Documentation is now authoritative. All bugs documented with exact fix instructions in `docs/components/REFACTOR_PLAN.md`. Story counter set to 039. Begin STORY-039 (Critical Bug Fixes). Key context:

1. Routes: `/dashboard/xxx` does NOT exist — correct URLs are `/chat`, `/inbox`, `/graph`, etc.
2. Onboarding is at `app/(auth)/onboarding/` — NOT under `(dashboard)`
3. Admin bypass MUST be implemented before any LLM feature testing (BUG-006)
4. `REFACTOR_PLAN.md` has exact code changes for every bug — use it as the implementation guide
5. `npm run build` must pass (0 TypeScript errors) before committing any story

---

## Backend Gate Checklist

Complete these before starting Phase B (frontend):

- [x] All backend stories merged to main — STORY-037 is last entry in `git log --oneline docs/stories/epics.md`
- [x] `make test` passes from clean checkout — 333 passed, 0 failures (2026-03-29)
- [x] `make quality` passes — 0 ruff errors, 0 pyright errors, 145 files formatted (2026-03-29)
- [x] `npm run generate-client` in ravenbase-web produces a non-empty `src/lib/api-client/` — ✅ 9 files generated (types.gen.ts, services.gen.ts, schemas.gen.ts, core/) (2026-03-30); fixed `--client axios` → `legacy/axios` (openapi-ts v0.53 API change)
- [x] `curl localhost:8000/health` responds — redis: ok; postgresql/qdrant/neo4j: error (cloud services unavailable in local dev; postgres + redis containers healthy per `docker compose ps`)

---

## How to Update This File

After every completed story, update the three fields above:
- **Current sprint** → increment by 1
- **Next story to implement** → next 🔲 row in `docs/stories/epics.md`
- **Last Completed Story** → the story you just finished + one sentence of what was built
- **Context for Next Session** → anything useful to know before starting the next story

**Also update `docs/.bmad/journal.md`** — append one entry for the completed story
following the template at the top of that file. This is mandatory and part of the same
commit (see `DEVELOPMENT_LOOP.md` → Step 9).

The agent that completes each story is responsible for updating all three docs files
as part of the final commit step (see `DEVELOPMENT_LOOP.md` → Post-Story Commit Template).

---

## Session Notes (freehand)

_Use this section for anything that doesn't fit the structure above:
blockers encountered, decisions made, deferred issues, environment quirks._

Brand color fix and UX quality gates added to all remaining stories STORY-031
through STORY-036. STORY-038 created as final polish story. Total stories
increased from 37 to 38.
