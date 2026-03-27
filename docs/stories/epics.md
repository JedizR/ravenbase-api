# Stories — Epics & Story Master List

> **Status key:** 🔲 DRAFT | ✅ DONE | 🔄 IN_PROGRESS | 🔍 IN_REVIEW
>
> **Total stories:** 37 | **Total epics:** 9
>
> **Execution order:** Stories within each epic must be completed in order (each builds on the previous). Epics must be completed before moving to the next epic.

---

## EPIC-01: Foundation Infrastructure

**Goal:** Every local service running, all DBs migrated, seed data working.
**Completion signal:** `make local-up && make seed && curl localhost:8000/health` returns all green.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-001 | API repo scaffold + Web repo scaffold + Makefile + Docker Compose | P0 | Medium | ✅ |
| STORY-002 | PostgreSQL schema + Alembic migrations | P0 | Medium | ✅ |
| STORY-003 | Qdrant + Neo4j initialization + constraints | P0 | Small | ✅ |
| STORY-004 | ARQ worker setup + health endpoint | P0 | Small | ✅ |

---

## EPIC-02: Ingestion Pipeline

**Goal:** User can upload a PDF, see real-time progress, and find text via search within 3 minutes.
**Completion signal:** Upload 10-page PDF via Postman → chunks appear in Qdrant → keyword search returns relevant results.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-005 | File upload endpoint + Supabase Storage | P0 | Medium | ✅ |
| STORY-006 | Docling parse + chunk + embed worker | P0 | Large | ✅ |
| STORY-007 | SSE progress stream (Redis pub/sub) | P0 | Medium | 🔲 |
| STORY-008 | Text quick-capture (Omnibar /ingest) | P0 | Small | 🔲 |

---

## EPIC-03: Knowledge Graph Layer

**Goal:** All ingested content appears as nodes/edges in Neo4j. Graph Explorer renders in browser.
**Completion signal:** Seed 2 PDFs → graph nodes visible in Neo4j Browser + rendered in Graph Explorer UI.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-009 | Entity extraction (Claude Haiku) + Neo4j writer | P0 | Large | ✅ |
| STORY-010 | Graph API endpoints (nodes + neighborhood) | P0 | Medium | ✅ |
| STORY-011 | Graph Explorer UI (Cytoscape.js, node click panel) | P1 | Large | 🔲 |

---

## EPIC-04: Conflict Detection & Memory Inbox

**Goal:** Ingesting contradictory facts creates Conflict records. User can resolve via all 3 flows.
**Completion signal:** Seed 2 contradicting documents → Conflict appears in DB → user resolves → Neo4j updates.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-012 | Conflict detection worker (Qdrant scan + LLM classify) | P0 | Large | ✅ |
| STORY-013 | Conflict API (list, resolve, undo) | P0 | Medium | ✅ |
| STORY-014 | Memory Inbox UI (keyboard navigation, 3 flows) | P0 | Large | 🔲 |

---

## EPIC-05: Meta-Document Generation

**Goal:** User can prompt "generate my resume" and receive a formatted Markdown document streamed in real-time.
**Completion signal:** Seed 20+ memory nodes → generate resume prompt → streaming output appears in Workstation.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-015 | Hybrid retrieval service (Qdrant + Neo4j) | P0 | Large | ✅ |
| STORY-016 | Meta-Doc generation worker (PII mask + LLM stream) | P0 | Large | 🔲 |
| STORY-017 | Workstation UI (SSE streaming, Markdown render, export) | P0 | Medium | 🔲 |

---

## EPIC-06: Authentication & System Profiles

**Goal:** New user can register, complete onboarding, create a System Profile, and switch contexts.
**Completion signal:** New user registers → creates "Work" profile → ingests file into that profile → search scoped to profile.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-018 | Clerk auth integration (FE + BE webhook) | P0 | Medium | 🔲 |
| STORY-019 | Onboarding wizard (profile creation + first upload) | P0 | Medium | 🔲 |
| STORY-020 | System Profile switching (Omnibar /profile command) | P1 | Small | 🔲 |

---

## EPIC-07: Marketing Site

**Goal:** Landing page converts visitors to signups. Lighthouse score > 90 mobile.
**Completion signal:** `npm run build` succeeds → Lighthouse CI passes → CTA links to `/register`.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-021 | Landing page (hero + features + workflow + CTA) | P1 | Large | 🔲 |
| STORY-022 | Pricing page + Stripe checkout integration | P1 | Medium | 🔲 |

---

## EPIC-08: Polish & Production Hardening

**Goal:** Credits system live, GDPR deletion tested, PII masking enabled, production checklist complete.
**Completion signal:** All items in `development/05-operations.md` production checklist checked.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-023 | Credits system (deduction, top-up, ledger) | P1 | Medium | 🔲 |
| STORY-024 | GDPR account deletion cascade | P1 | Medium | 🔲 |
| STORY-025 | PII masking in production + Presidio config | P1 | Medium | 🔲 |
| STORY-031 | Dark mode toggle (localStorage + .dark class) | P1 | Small | 🔲 |
| STORY-032 | Transactional email (welcome, low-credits, ingestion complete via Resend) | P1 | Medium | 🔲 |
| STORY-033 | Legal pages (Privacy Policy, Terms of Service, Cookie Consent) | P0 | Small | 🔲 |
| STORY-034 | Referral system (code gen, reward on first upload, Settings → Referrals) | P1 | Medium | 🔲 |
| STORY-035 | Data export / portability (multi-store ZIP, email link, Settings → Data) | P1 | Medium | 🔲 |
| STORY-036 | Internal admin dashboard (user management, credit adjustment, stats) | P1 | Medium | 🔲 |
| STORY-037 | Cold data lifecycle — inactivity archival for Free-tier users (CRON, warning email, data purge) | P1 | Medium | 🔲 |

---

---

## EPIC-09: Memory Intelligence

**Goal:** Elevate Ravenbase from document synthesis into an interactive memory companion.
Users can converse with their knowledge base, import context from any AI chat, and
query the knowledge graph in plain English.
**Completion signal:** All 5 stories passing. User can: ask a question and get a streamed
answer with citations; import a pasted AI chat response; query the graph in English and
see highlighted results.

| Story | Title | Priority | Complexity | Status |
|---|---|---|---|---|
| STORY-026 | Conversational memory chat — backend | P0 | Large | 🔲 |
| STORY-027 | Conversational memory chat — frontend | P0 | Large | 🔲 |
| STORY-028 | AI chat context import helper | P1 | Medium | 🔲 |
| STORY-029 | Natural language graph query — backend | P1 | Medium | 🔲 |
| STORY-030 | Natural language graph query — frontend | P1 | Medium | 🔲 |

---

## Story File Locations

```
docs/stories/
├── EPIC-01-foundation/
│   ├── STORY-001.md
│   ├── STORY-002.md
│   ├── STORY-003.md
│   └── STORY-004.md
├── EPIC-02-ingestion/
│   ├── STORY-005.md
│   ├── STORY-006.md
│   ├── STORY-007.md
│   └── STORY-008.md
├── EPIC-03-graph/
│   ├── STORY-009.md
│   ├── STORY-010.md
│   └── STORY-011.md
├── EPIC-04-conflict/
│   ├── STORY-012.md
│   ├── STORY-013.md
│   └── STORY-014.md
├── EPIC-05-metadoc/
│   ├── STORY-015.md
│   ├── STORY-016.md
│   └── STORY-017.md
├── EPIC-06-auth-profiles/
│   ├── STORY-018.md
│   ├── STORY-019.md
│   └── STORY-020.md
├── EPIC-07-marketing/
│   ├── STORY-021.md
│   └── STORY-022.md
├── EPIC-08-polish/
│   ├── STORY-023.md
│   ├── STORY-024.md
│   ├── STORY-025.md
│   ├── STORY-031.md
│   ├── STORY-032.md
│   ├── STORY-033.md
│   ├── STORY-034.md
│   ├── STORY-035.md
│   ├── STORY-036.md
│   └── STORY-037.md
└── EPIC-09-memory-intelligence/
    ├── STORY-026.md
    ├── STORY-027.md
    ├── STORY-028.md
    ├── STORY-029.md
    └── STORY-030.md
```
