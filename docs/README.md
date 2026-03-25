# Ravenbase — Documentation Master Index

> **Status:** PRE-DEVELOPMENT | All planning complete | Ready for BMAD story execution
> **Last Updated:** March 2026 | **Author:** Natakorn Wannabovorn (Jedi)

---

## What This Is

This `docs/` directory contains the **complete planning corpus** for the Ravenbase platform — a Human-AI Long-Term Context Memory System built as a production-grade SaaS.

All documents are optimized for **agent readability** (Claude Code + BMAD workflow). Every file follows a strict structure designed to give an AI coding agent exactly the context it needs — no more, no less.

---

## How to Use This (BMAD Workflow)

> **New here?** Read `KICKSTART.md` first — it's the definitive getting-started guide with exact commands.
> Running two repos in parallel? Read `PARALLEL_DEV_GUIDE.md` for the parallelism rules.

```
┌─────────────────────────────────────────────────────────────┐
│  PLANNING (complete) → AUDIT → DEVELOPMENT                  │
│                                                             │
│  1. Run Claude Code audit (CLAUDE_CODE_AUDIT_PROMPT.md)     │
│     on this /docs folder to verify readiness                │
│                                                             │
│  2. Follow KICKSTART.md to set up both repos                │
│                                                             │
│  3. Pick next story from stories/epics.md (🔲 = ready)      │
│                                                             │
│  4. Open Claude Code in the correct repo:                   │
│     Backend story → ravenbase-api/                          │
│     Frontend story → ravenbase-web/                         │
│                                                             │
│  5. Paste the story prompt from KICKSTART.md Phase 5        │
│                                                             │
│  6. Review plan → Approve → Implement → Quality gate        │
│     make quality && make test  (backend)                    │
│     npm run build && npm run test  (frontend)               │
│                                                             │
│  7. Mark story ✅ in stories/epics.md → commit → PR → merge │
└─────────────────────────────────────────────────────────────┘
```

**Before starting any story, always load:**
1. `CLAUDE.md` in the repo root (architecture rules)
2. The story file: `docs/stories/EPIC-XX-name/STORY-XXX.md`
3. Referenced architecture files listed in the story's "Context" section

---

## Directory Structure

```
docs/
├── README.md                          ← You are here
├── KICKSTART.md                       ← START HERE — full getting started guide
├── PARALLEL_DEV_GUIDE.md              ← How to run 2 repos simultaneously
├── CLAUDE_CODE_AUDIT_PROMPT.md        ← Paste into Claude Code for pre-dev audit
├── AUDIT_REPORT.md                    ← Corpus quality analysis
├── CLAUDE.md                          ← Master agent instructions (root)
│
├── prd/                               ← Product Requirements
│   ├── 00-executive-summary.md        ← Vision, differentiators, success metrics
│   ├── 01-problem-statement.md        ← Pain points, market, competitor matrix
│   ├── 02-personas.md                 ← User personas with JTBD
│   ├── 03-feature-specs/              ← One file per feature
│   │   ├── F1-ingestion.md
│   │   ├── F2-knowledge-graph.md
│   │   ├── F3-memory-inbox.md
│   │   ├── F4-meta-document.md
│   │   ├── F5-graph-explorer.md
│   │   ├── F6-omnibar.md
│   │   └── F7-system-profiles.md
│   ├── 04-non-functional-requirements.md ← SLAs, security, compliance
│   └── 05-monetization.md             ← Pricing, credits, GTM
│
├── architecture/                      ← Technical Architecture
│   ├── 00-system-overview.md          ← Service map, data flow, deployment
│   ├── 01-tech-stack-decisions.md     ← ADRs for every major choice
│   ├── 02-database-schema.md          ← PostgreSQL DDL + Neo4j + Qdrant
│   ├── 03-api-contract.md             ← All endpoints, request/response shapes
│   ├── 04-background-jobs.md          ← ARQ queue spec, worker patterns, retry
│   ├── 05-security-privacy.md         ← Multi-tenancy, PII, GDPR, encryption
│   └── 06-observability.md            ← Logging, metrics, tracing, alerting
│
├── design/                            ← UX/UI Design System
│   ├── 00-brand-identity.md           ← Brand values, voice, personality
│   ├── 01-design-system.md            ← Colors, typography, spacing, tokens
│   ├── 02-component-library.md        ← shadcn components + custom components
│   ├── 03-screen-flows.md             ← All page flows, layouts, wireframes
│   └── 04-ux-patterns.md              ← Interactions, animations, states
│
├── development/                       ← Development Standards
│   ├── 00-project-structure.md        ← Repo layout, file conventions
│   ├── 01-dev-environment.md          ← Setup guide, docker-compose, env vars
│   ├── 02-coding-standards.md         ← Layer architecture, code style, patterns
│   ├── 03-testing-strategy.md         ← Test pyramid, fixtures, CI
│   ├── 04-deployment.md               ← Railway + Vercel + GitHub Actions CD
│   └── 05-operations.md               ← Monitoring, incidents, rollback
│
└── stories/                           ← BMAD Story Files
    ├── README.md                      ← Story template + workflow guide
    ├── epics.md                       ← All epics + story list + status
    ├── EPIC-01-foundation/            ← Infrastructure + DB setup
    ├── EPIC-02-ingestion/             ← File upload + Docling + embeddings
    ├── EPIC-03-graph/                 ← Neo4j entity extraction + Graph UI
    ├── EPIC-04-conflict/              ← Conflict detection + Memory Inbox UI
    ├── EPIC-05-metadoc/               ← Meta-Document generation + Workstation
    ├── EPIC-06-auth-profiles/         ← Auth + onboarding + System Profiles
    ├── EPIC-07-marketing/             ← Landing page + pricing page
    └── EPIC-08-polish/                ← Credits + GDPR + PII masking
```

---

## Document Cross-Reference Map

| When working on... | Required reading |
|---|---|
| Any backend feature | `architecture/00-system-overview.md`, `architecture/02-database-schema.md`, `development/02-coding-standards.md` |
| Any frontend feature | `design/01-design-system.md`, `design/02-component-library.md`, `design/03-screen-flows.md` |
| Ingestion pipeline | `prd/03-feature-specs/F1-ingestion.md`, `architecture/04-background-jobs.md` |
| Knowledge graph | `prd/03-feature-specs/F2-knowledge-graph.md`, `architecture/02-database-schema.md` |
| Memory Inbox | `prd/03-feature-specs/F3-memory-inbox.md`, `design/04-ux-patterns.md` |
| Meta-Document | `prd/03-feature-specs/F4-meta-document.md`, `architecture/03-api-contract.md` |
| Security/privacy | `architecture/05-security-privacy.md`, `prd/04-non-functional-requirements.md` |
| Deployment | `development/04-deployment.md`, `development/05-operations.md` |

---

## Story Execution Order

Stories follow a backend-complete first strategy. See `PARALLEL_DEV_GUIDE.md` for the full sprint sequence.

**Phase A — Backend (Sprints 1–17):**
```
EPIC 01 Foundation      → STORIES 001–004   (infra, DBs, queues)
EPIC 02 Ingestion BE    → STORIES 005–008   (upload, parse, embed, SSE backend)
EPIC 03 Knowledge Graph → STORIES 009–010   (extract, write, graph API)
EPIC 04 Conflict BE     → STORIES 012–013   (detect, resolve API)
EPIC 05 Meta-Document   → STORIES 015–016   (retrieval, generation)
EPIC 06 Auth BE         → STORY 018-BE      (auth, webhooks)
EPIC 08 Polish          → STORIES 023–025   (credits, GDPR, PII masking)
```

**Phase B — Frontend (Sprints 18–34, after all backend merged + tests passing):**
```
Web scaffold            → STORY 001-WEB     (Next.js 15 + design system)
Auth FE                 → STORY 018-FE      (login, register, middleware)
Profiles + Onboarding   → STORIES 019–020   (onboarding wizard, profile switching)
Ingestion FE            → STORIES 007-FE + 008  (progress component, omnibar)
Graph Explorer          → STORY 011         (Cytoscape.js force-directed graph)
Conflict Inbox          → STORY 014         (keyboard navigation, 3 flows)
Workstation             → STORY 017         (SSE streaming, Markdown render)
Marketing               → STORIES 021–022   (landing, pricing — no backend dep)
```

**Total: 37 stories** — no time target; quality gate must pass before each story is marked done.

---

## Key Architectural Decisions (TL;DR)

| Decision | Choice | Why |
|---|---|---|
| Repo structure | **2 separate repos** | FE/BE deploy independently; per BMAD blueprint |
| Backend queue | **ARQ + Redis** (Python) | Python-native async queue; NOT BullMQ (Node.js) |
| Auth provider | **Clerk** | Single provider for FE + BE; no JWT sync issues |
| FE→BE contract | **Auto-generated OpenAPI client** | Zero manual type duplication; NOT tRPC |
| Vector store | **Qdrant** | Purpose-built vector store; simpler, cheaper, Docker-friendly |
| Graph DB | **Neo4j AuraDB Free** → AuraDB Pro | Free: 50K nodes (enough for MVP) |
| Migrations | **Alembic** | Industry standard; never `create_all()` in prod |
| Logging | **structlog** | Structured JSON; trace IDs on every request |
| Monitoring | **Sentry** (errors) + **Grafana Cloud** (metrics) | Both free tiers sufficient for MVP |
| Timeline | 18 backend sprints + 17 frontend sprints = 35 total sprints (no time target) | |
| Strategy | Backend-complete first: all backend stories merged + tests passing → then frontend | |

---

## Definition of Done (Project-Level)

Before calling Ravenbase v1.0 "done":
- [ ] All 37 stories implemented and tests passing
- [ ] Production checklist from `development/05-operations.md` fully reviewed
- [ ] p95 query latency < 500ms measured in staging
- [ ] GDPR deletion cascade tested end-to-end
- [ ] 10 beta users actively using the platform
- [ ] Landing page Lighthouse score > 90 on mobile
- [ ] Zero `print()` statements — all observability via structlog
- [ ] `make quality && make test` passes in CI
