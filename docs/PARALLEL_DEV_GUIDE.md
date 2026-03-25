# Parallel Development Guide — Two Repos, Two Claude Code Sessions

> **Answer to "Can 2 repos be developed in parallel?"**
> **Yes — but only for specific story combinations. This guide tells you exactly which ones.**

---

## The Core Answer

The two repos have **hard dependencies** (backend must exist before frontend can call it) and **fully independent** tracks (some frontend work needs zero backend).

You can run two Claude Code sessions simultaneously when:
- Session A is on a **backend-only story** in `ravenbase-api`
- Session B is on a **frontend-only, API-independent story** in `ravenbase-web`

You must run sequentially when:
- A frontend story calls backend endpoints that do not exist yet
- Both sessions would modify the same shared contract (OpenAPI spec)

---

## Story Assignment Map

Every story is classified by which repo it lives in:

```
REPO: ravenbase-api (Python/FastAPI)
────────────────────────────────────────
STORY-001  Scaffold API repo + Makefile + Docker Compose
STORY-002  PostgreSQL schema + Alembic migrations
STORY-003  Qdrant + Neo4j initialization
STORY-004  ARQ worker setup + health endpoint
STORY-005  File upload endpoint + Supabase Storage
STORY-006  Docling parse + chunk + embed worker
STORY-007  SSE progress stream backend (Redis pub/sub)
STORY-009  Entity extraction worker + Neo4j writer
STORY-010  Graph API endpoints
STORY-012  Conflict detection worker
STORY-013  Conflict API (list, resolve, undo)
STORY-015  Hybrid retrieval service
STORY-016  Meta-Doc generation worker + streaming
STORY-018  Clerk auth backend (require_user + webhooks)
STORY-023  Credits system
STORY-024  GDPR account deletion cascade
STORY-025  PII masking + Presidio config

REPO: ravenbase-web (Next.js 15)
────────────────────────────────────────
STORY-007  IngestionProgress component (SSE subscriber)   ← shares a story number with backend
STORY-008  Omnibar /ingest command (quick-capture UI)
STORY-011  Graph Explorer UI (Cytoscape.js)
STORY-014  Memory Inbox UI (keyboard navigation, 3 flows)
STORY-017  Workstation UI (SSE streaming + Markdown)
STORY-018  Clerk auth frontend (SignIn, SignUp, middleware)  ← shares a story number with backend
STORY-019  Onboarding wizard
STORY-020  System Profile switching UI
STORY-021  Landing page (marketing)
STORY-022  Pricing page + Stripe checkout UI

NOTE: STORY-007 and STORY-018 each span both repos.
Work the backend half first, then the frontend half.
```

---

## Development Strategy: Backend-Complete First

All backend stories are completed — with all tests passing — before any dashboard
frontend work begins. This eliminates stub debt and gives the frontend agent a complete,
tested API surface to build against.

### Why Backend-Complete First

**Eliminates stub drift.** When frontend is built against mocked endpoints, the mocks
inevitably diverge from the real API. Every divergence costs a debugging session when
the real backend is wired in. Backend-complete means the frontend agent works against
real types from day one.

**Better agent context.** A frontend agent opening STORY-011 (Graph Explorer) with a
complete backend can read the actual OpenAPI spec — it knows the exact shape of every
node object, every pagination response, every error code. No guessing.

**Cleaner sprint tracking.** Backend and frontend are sequenced, not concurrent. The
sprint board tells you exactly where you are in a linear sequence, not across two
simultaneous tracks.

### The Exception: Marketing Stories

STORY-021 (Landing page) and STORY-022 (Pricing page) have zero backend dependencies.
They are pure Next.js + Tailwind + Framer Motion. They can be implemented any time —
during the backend phase, after it, or whenever you want a change of context.
They are NOT blocked by any backend story.

### Backend-Complete Gate

Before starting ANY dashboard frontend story (STORY-007-FE and beyond), verify:
- [ ] All backend stories are merged to main
- [ ] `make test` passes with 0 failures from a clean checkout
- [ ] `make quality` passes with 0 errors
- [ ] `npm run generate-client` runs without error and produces a non-empty `src/lib/api-client/`
- [ ] `curl api.ravenbase.app/health` returns all 4 services healthy (or local equivalent)

---

## Sprint Sequence

Each sprint = one or two tightly related stories. Start the next sprint only when the
current sprint's Definition of Done is fully checked. There are no time deadlines.

### Phase A — Backend (Sprints 1–17)

| Sprint | Stories | Completion Signal |
|---|---|---|
| 1 | STORY-001 | `make quality` passes. `curl :8000/health` → `{"status":"ok"}` |
| 2 | STORY-002 | `make db-upgrade` migrates clean. All 7 tables exist in DB |
| 3 | STORY-003 + STORY-004 | Health endpoint shows qdrant+neo4j ok. ARQ worker starts |
| 4 | STORY-005 | Upload returns 202. File in Supabase Storage. Source row in DB |
| 5 | STORY-006 | PDF fully parsed + embedded. Chunks searchable in Qdrant |
| 6 | STORY-007-BE | SSE stream emits progress events to curl client |
| 7 | STORY-008-BE | `/v1/ingest/text` endpoint accepts and queues text |
| 8 | STORY-009 + STORY-010 | Neo4j nodes populated. Graph API returns nodes+edges |
| 9 | STORY-012 + STORY-013 | Conflict detected + stored. Resolve endpoint works. Undo works |
| 10 | STORY-015 + STORY-016 | Hybrid retrieval returns ranked chunks. MetaDoc streams via SSE |
| 11 | STORY-018-BE | JWT validated. Webhook creates User in DB |
| 12 | STORY-023 | Credits deducted per operation. 402 on insufficient balance |
| 13 | STORY-024 | Full cascade deletion verified across all 4 stores |
| 14 | STORY-025 | PII masking active in production config. Tests pass |
| 15 | STORY-026 | Chat endpoint streams tokens. Multi-turn session created. Credits deducted |
| 16 | STORY-028-BE | `GET /v1/ingest/import-prompt` returns personalized prompt |
| 17 | STORY-029 | Graph query returns cypher + nodes. Safety rejects write operations |

**Backend complete gate (between Sprint 17 and Sprint 18):**
`make test` → 0 failures. `npm run generate-client` → complete typed client generated.

### Phase B — Frontend (Sprints 18–34)

Phase B begins only after Phase A backend gate passes.

| Sprint | Stories | Completion Signal |
|---|---|---|
| 18 | STORY-001-WEB (web repo scaffold) | `npm run build` passes. Fonts load. Design tokens active |
| 19 | STORY-018-FE | Register → login → reach `/dashboard`. JWT on API calls |
| 20 | STORY-019 + STORY-020 | Onboarding wizard works. Profile switching works |
| 21 | STORY-007-FE + STORY-008-FE | IngestionProgress streams. Omnibar captures text |
| 22 | STORY-011 | Graph Explorer renders force-directed graph. Node click opens panel |
| 23 | STORY-014 | Memory Inbox keyboard nav. All 3 flows work end-to-end |
| 24 | STORY-017 | Workstation streams Markdown. Export to .md works |
| 25 | STORY-021 + STORY-022 | Landing page live. Pricing page + Stripe checkout works |
| 26 | STORY-027 | Chat UI streams tokens. Citations link to graph nodes. Sessions persist |
| 27 | STORY-028-FE | Import helper UI: copy prompt, paste response, submit ingest |
| 28 | STORY-030 | Query bar in Graph Explorer. Matching nodes highlight amber |
| 29 | STORY-031 | Dark mode toggle works. No flash. Preference persists. |
| 30 | STORY-032 | Welcome email sends. Low-credits warning sends. Ingestion complete for large files sends. |
| 31 | STORY-033 | Privacy Policy and Terms pages render. Footer has legal links. Cookie banner conditional on PostHog. |
| 32 | STORY-034 | Referral codes working. Settings → Referrals page renders. Copy link works. |
| 33 | STORY-035 | Export job completes. ZIP in Supabase. Email with download link sent. Settings → Data renders. |
| 34 | STORY-036 | Admin dashboard live. Credit adjustment works. Stats page shows real data. Non-admins redirected. |
| 35 | STORY-037 | Activity middleware tracking last_active_at. CRON task running. Warning email sent at day 150. Data purge at day 180. Pro/Team/admin users untouched. |

**Optional (any time during Phase A or B):**
STORY-021 and STORY-022 can be done during any lull in Phase A — they have no backend dependency.

---

## The Golden Rule of Parallel Sessions

**The contract between repos is `architecture/03-api-contract.md` + the generated OpenAPI client.**

Before the frontend agent can call a backend endpoint, that endpoint must:
1. Exist in the running backend (`make dev-up` + API server running)
2. Have been regenerated into the client: `npm run generate-client` in `ravenbase-web`

**If an endpoint doesn't exist yet:** The frontend agent should use `msw` (Mock Service Worker) to mock the response, or simply skip the API call and use hardcoded stub data, with a `TODO: connect to API` comment. Do NOT have the frontend agent invent its own fetch calls.

---

## Docs Suitability for Parallel Sessions

The current docs are structured for parallel work with these notes:

| What works well | What needs attention |
|---|---|
| `CLAUDE.md` is self-contained per-repo context | The web repo needs its own `CLAUDE_FRONTEND.md` at root (provided in `design/CLAUDE_FRONTEND.md`) |
| Every story file lists which repo it belongs to | Stories 007 and 018 span both repos — each session only does its half |
| `architecture/03-api-contract.md` is the shared contract | Both agents must read this; never let an agent invent endpoint shapes |
| Design system is complete enough for frontend to work ahead | Frontend must read `design/01-design-system.md` before touching any component |
| Story files list explicit file paths and AC | Each session knows exactly what it's producing without reading the other repo |

---

## What Each Repo's CLAUDE.md Should Contain

Copy the root `docs/CLAUDE.md` to `ravenbase-api/CLAUDE.md`.
Copy `docs/design/CLAUDE_FRONTEND.md` to `ravenbase-web/CLAUDE_FRONTEND.md` and rename it `CLAUDE.md` there.

The backend CLAUDE.md already exists. The frontend CLAUDE.md (`design/CLAUDE_FRONTEND.md`) needs to be placed at `ravenbase-web/CLAUDE.md` — it contains all the frontend-specific rules (no form tags, Tailwind-only, Zod validation, apiFetch pattern, dark/light mode rules).

---

## Session Isolation: What Each Agent Needs to Know

When you open a Claude Code session in `ravenbase-api/`, you say:

> "Read CLAUDE.md. Read docs/stories/[EPIC-XX]/[STORY-XXX].md. Show plan first."

When you open a Claude Code session in `ravenbase-web/`, you say:

> "Read CLAUDE.md (the frontend rules). Read docs/design/01-design-system.md. Read docs/stories/[EPIC-XX]/[STORY-XXX].md. Show plan first."

Each session only needs its own repo context. Neither agent needs to read the other repo's code. The shared contract lives in `docs/architecture/03-api-contract.md`.
