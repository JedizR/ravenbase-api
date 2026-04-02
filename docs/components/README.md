# Ravenbase — Component Registry

> Agent instruction: Every story belongs to a component. When implementing
> a story, read the relevant component spec to understand the full scope
> of what this component does and what architectural constraints apply.
> Do not let one component's concerns leak into another's files.

## Component Map

| Component | ID | FRs | Key Source Files | Stories |
|---|---|---|---|---|
| IngestionPipeline | BE-COMP-01 | FR-01, FR-02 | src/api/routes/ingest.py, src/services/ingestion_service.py, src/workers/ingestion_tasks.py, src/adapters/storage_adapter.py, src/adapters/docling_adapter.py, src/adapters/openai_adapter.py, src/adapters/moderation_adapter.py | 005, 006, 007, 008 |
| GraphEngine | BE-COMP-02 | FR-03, FR-04, FR-05, FR-06, FR-13 | src/services/graph_service.py, src/workers/graph_tasks.py, src/adapters/neo4j_adapter.py, src/adapters/llm_router.py, src/api/routes/graph.py | 009, 010, 012, 013, 029 |
| RetrievalEngine | BE-COMP-03 | FR-07, FR-08 | src/services/retrieval_service.py, src/adapters/qdrant_adapter.py | 015, 016 |
| GenerationEngine | BE-COMP-04 | FR-08, FR-12 | src/services/generation_service.py, src/workers/generation_tasks.py | 016, 026 |
| AuthSystem | BE-COMP-05 | FR-09 | src/api/dependencies/auth.py | 018 |
| CreditSystem | BE-COMP-06 | FR-10 | src/services/credit_service.py | 023 |
| PrivacyLayer | BE-COMP-07 | FR-11 | src/services/privacy_service.py, src/adapters/presidio_adapter.py | 024, 025 |
| LandingPage | FE-COMP-01 | — | app/(marketing)/page.tsx, components/marketing/*.tsx | 021 |
| PricingPage | FE-COMP-02 | — | app/(marketing)/pricing/page.tsx, components/marketing/Pricing*.tsx | 022 |
| OnboardingWizard | FE-COMP-03 | — | app/(auth)/onboarding/page.tsx, components/domain/OnboardingWizard.tsx | 019 |
| Omnibar | FE-COMP-04 | — | components/domain/Omnibar.tsx, hooks/use-omnibar.ts | 008, 020 |
| MemoryInbox | FE-COMP-05 | — | components/domain/MemoryInbox.tsx, components/domain/ConflictCard.tsx | 014 |
| GraphExplorer | FE-COMP-06 | — | components/domain/GraphExplorer.tsx, components/domain/GraphNodePanel.tsx | 011, 030 |
| Workstation | FE-COMP-07 | — | components/domain/Workstation.tsx, components/domain/MetaDocEditor.tsx | 017 |

---

## BE-COMP-01: IngestionPipeline

**Purpose:** Everything from file upload through indexed chunks.
Owns the full ingestion lifecycle from HTTP request to Qdrant upsert.

**Boundaries:**
- Owns: file validation, MIME detection, SHA-256 dedup, Supabase Storage,
  Docling parsing, chunking, OpenAI embedding, Qdrant upsert,
  content moderation, status transitions, rate limiting
- Does NOT own: entity extraction (BE-COMP-02), retrieval (BE-COMP-03),
  authentication (BE-COMP-05)

**Critical invariants:**
- tenant_id included in every Qdrant payload point
- Source status always transitions PENDING → PROCESSING → INDEXING → COMPLETED
- graph_extraction always enqueued after COMPLETED
- No ARQ retry on failure (no re-raise in except block)

---

## BE-COMP-02: GraphEngine

**Purpose:** Knowledge graph construction, exploration, conflict
detection and resolution, and natural language graph queries.

**Boundaries:**
- Owns: Neo4j writes (Concept MERGE, Memory CREATE), graph API endpoints,
  LLMRouter calls for entity extraction and Cypher generation,
  conflict detection worker, conflict resolution API
- Does NOT own: chunk retrieval for generation (BE-COMP-03),
  authentication (BE-COMP-05)

**Critical invariants:**
- Concept nodes use MERGE, never CREATE (deduplication by {name, tenant_id})
- All Cypher queries pass tenant_id as a parameter — never f-string
- Cypher generation validates output is read-only before executing
- Chunk failures in graph_extraction are logged and skipped — do not abort

---

## BE-COMP-03: RetrievalEngine

**Purpose:** Hybrid retrieval combining Qdrant semantic search with
Neo4j graph-neighbor boosting.

**Boundaries:**
- Owns: hybrid search logic, result ranking, profile-scoped filtering
- Does NOT own: LLM generation (BE-COMP-04), graph writes (BE-COMP-02)

**Critical invariants:**
- All Qdrant queries use _tenant_filter() — never bypass it
- Results always scoped to tenant_id from JWT

---

## BE-COMP-04: GenerationEngine

**Purpose:** LLM-driven document generation and conversational chat,
with PII masking and SSE streaming.

**Boundaries:**
- Owns: meta-document generation, chat session management,
  streaming SSE responses, citation attachment
- Does NOT own: retrieval (BE-COMP-03), privacy/PII masking (BE-COMP-07)

---

## BE-COMP-05: AuthSystem

**Purpose:** JWT validation, Clerk webhook handling, and the
require_user/verify_token_query_param FastAPI dependencies.

**Boundaries:**
- Owns: all JWT decode logic, Clerk JWKS client, webhook handler
- Does NOT own: any business logic — thin gateway only

**Critical invariants:**
- tenant_id always extracted from JWT sub claim
- Never accept user_id from request body or query params

---

## BE-COMP-06: CreditSystem

**Purpose:** Per-operation credit deduction with ledger tracking.

**Boundaries:**
- Owns: credit balance checks, deduction, CreditTransaction writes
- Integrates with all other components that call LLM or storage APIs

---

## BE-COMP-07: PrivacyLayer

**Purpose:** GDPR-compliant cascade deletion and PII masking.

**Boundaries:**
- Owns: cross-store deletion (PostgreSQL, Qdrant, Neo4j, Supabase),
  Presidio PII detection and masking
- Does NOT own: the stores themselves (delegates to adapters)

---

## FE-COMP-01: LandingPage

**Purpose:** SEO-optimized marketing landing page that converts visitors to signups.

**Boundaries:**
- Owns: Hero, How It Works, Features, Testimonials, FAQ, CTA, Footer
- Does NOT own: auth (BE-COMP-05), pricing logic (FE-COMP-02)

---

## FE-COMP-02: PricingPage

**Purpose:** Pricing tiers page with Stripe Checkout integration.

**Boundaries:**
- Owns: Pricing tiers (Free/Pro/Team), annual/monthly toggle, Stripe Checkout
- Does NOT own: billing webhook processing (BE-COMP-07)

---

## FE-COMP-03: OnboardingWizard

**Purpose:** First-experience wizard for new users — profile creation + optional first upload.

**Boundaries:**
- Owns: Multi-step wizard (profile name → file upload), redirect logic
- Does NOT own: ingestion pipeline (BE-COMP-01), auth (BE-COMP-05)

---

## FE-COMP-04: Omnibar

**Purpose:** Global keyboard-driven command interface (Cmd+K). Slash commands for quick text capture and profile switching.

**Boundaries:**
- Owns: /ingest text capture, /profile switching, command detection
- Does NOT own: ingestion pipeline (BE-COMP-01), profile management (BE-COMP-05)

---

## FE-COMP-05: MemoryInbox

**Purpose:** Keyboard-first conflict resolution interface with 3 resolution flows (Binary Triage, Conversational, Auto-resolved with Undo).

**Boundaries:**
- Owns: Conflict card UI, keyboard navigation (J/K/Enter/Backspace/C), optimistic updates
- Does NOT own: conflict detection worker (BE-COMP-02), conflict resolution API (BE-COMP-02)

---

## FE-COMP-06: GraphExplorer

**Purpose:** Cytoscape.js-based visual knowledge graph explorer with filtering, node detail panel, and mobile list fallback.

**Boundaries:**
- Owns: Graph visualization, node detail panel, filters, neighborhood expansion
- Does NOT own: graph API endpoints (BE-COMP-02), conflict detection (BE-COMP-02)

---

## FE-COMP-07: Workstation

**Purpose:** Meta-Document generation workspace with real-time SSE streaming, Markdown rendering, and export functionality.

**Boundaries:**
- Owns: Streaming editor, document history, prompt input, export (MD/PDF)
- Does NOT own: Meta-Doc generation pipeline (BE-COMP-04), retrieval (BE-COMP-03)

---

## Authoritative Route Map

**CRITICAL:** Next.js route groups `(auth)`, `(marketing)`, `(dashboard)` are FOLDER grouping ONLY. They do NOT appear in the URL. `/dashboard/chat` does NOT exist — the correct URL is `/chat`.

```
/                         → app/(marketing)/page.tsx
/pricing                  → app/(marketing)/pricing/page.tsx
/privacy                  → app/(marketing)/privacy/page.tsx
/terms                    → app/(marketing)/terms/page.tsx
/login                    → app/(auth)/login/[[...rest]]/page.tsx
/register                 → app/(auth)/register/[[...rest]]/page.tsx
/onboarding               → app/(auth)/onboarding/page.tsx      ← NOT under (dashboard)
/chat                     → app/(dashboard)/chat/page.tsx
/inbox                    → app/(dashboard)/inbox/page.tsx
/graph                    → app/(dashboard)/graph/page.tsx
/sources                  → app/(dashboard)/sources/page.tsx
/workstation              → app/(dashboard)/workstation/page.tsx
/settings/*               → app/(dashboard)/settings/*/page.tsx
/admin/*                  → app/admin/*/page.tsx
/dashboard                → app/(dashboard)/page.tsx  [needs creation → redirect("/chat")]
```

**Forbidden URL patterns** (these do NOT exist):
```
/dashboard/chat           ← WRONG — use /chat
/dashboard/inbox          ← WRONG — use /inbox
/dashboard/graph          ← WRONG — use /graph
/dashboard/sources        ← WRONG — use /sources
/dashboard/workstation    ← WRONG — use /workstation
/dashboard/onboarding     ← WRONG — use /onboarding
```

---

## Admin Bypass System Overview

Admin users are identified by the `ADMIN_USER_IDS` env var (comma-separated Clerk user IDs).

**Backend behavior:**
- `CreditService.check_or_raise()` returns early for admin users — never blocks
- `CreditService.deduct()` returns a zero-amount `CreditTransaction` — balance unchanged
- `GET /v1/me` returns `{is_admin: true}` for admin users
- All features work for admins without any credits or subscription

**Frontend behavior:**
- Sidebar: shows `◆ ADMIN_ACCESS` instead of credit balance when `user.is_admin = true`
- Pricing page: shows "Admin Account — Full Access Bypass Active" instead of tier cards
- All other UI unchanged — admin users see the same interface as regular users

**BUG-006:** Admin bypass is NOT YET IMPLEMENTED in `src/services/credit_service.py`. This blocks all end-to-end testing of LLM features. Fix in STORY-040.

---

## Cross-Reference Map

When implementing any feature, read docs in this order:

1. **Component spec** (`docs/components/[COMP-ID]-[Name].md`) — user journey, API contracts, admin bypass, known bugs
2. **Design preamble** (`docs/design/AGENT_DESIGN_PREAMBLE.md`) — ALWAYS before any JSX
3. **Design system** (`docs/design/01-design-system.md`) — color tokens, typography, spacing
4. **API contract** (`docs/architecture/03-api-contract.md`) — endpoint schemas
5. **Database schema** (`docs/architecture/02-database-schema.md`) — data model
6. **REFACTOR_PLAN.md** (`docs/components/REFACTOR_PLAN.md`) — specific bug fix instructions

**Component-to-component dependencies:**
```
FE-COMP-01 (Landing)        → reads: design/*
FE-COMP-02 (Pricing)        → reads: BE-COMP-06 (credits/admin bypass)
FE-COMP-03 (Onboarding)     → reads: BE-COMP-05 (auth), BE-COMP-01 (ingest)
FE-COMP-04 (Omnibar)        → reads: BE-COMP-01 (text ingest)
FE-COMP-05 (MemoryInbox)    → reads: BE-COMP-02 (conflict detection/resolution)
FE-COMP-06 (GraphExplorer)  → reads: BE-COMP-02 (graph API)
FE-COMP-07 (Workstation)    → reads: BE-COMP-04 (generation), BE-COMP-06 (credits)
BE-COMP-01 (Ingestion)      → reads: BE-COMP-06 (credits)
BE-COMP-02 (GraphEngine)    → reads: BE-COMP-06 (credits for NL queries)
BE-COMP-03 (Retrieval)      → reads: BE-COMP-01, BE-COMP-02 (sources for retrieval)
BE-COMP-04 (Generation)     → reads: BE-COMP-03 (retrieval), BE-COMP-06 (credits), BE-COMP-07 (PII)
BE-COMP-05 (Auth)           → reads: BE-COMP-06 (signup bonus)
BE-COMP-06 (Credits)        → reads: all other BE-COMP files (credit costs)
BE-COMP-07 (Privacy)        → reads: BE-COMP-04 (PII masking in generation)
```
