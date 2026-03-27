# Ravenbase — Component Registry

> Agent instruction: Every story belongs to a component. When implementing
> a story, read the relevant component spec to understand the full scope
> of what this component does and what architectural constraints apply.
> Do not let one component's concerns leak into another's files.

## Component Map

| Component | ID | FRs | Key Source Files | Stories |
|---|---|---|---|---|
| IngestionPipeline | COMP-01 | FR-01, FR-02 | src/services/ingestion_service.py, src/workers/ingestion_tasks.py, src/adapters/storage_adapter.py, src/adapters/docling_adapter.py, src/adapters/openai_adapter.py, src/adapters/moderation_adapter.py | 005, 006, 007, 008 |
| GraphEngine | COMP-02 | FR-03, FR-04, FR-05, FR-06, FR-13 | src/services/graph_service.py, src/workers/graph_tasks.py, src/adapters/neo4j_adapter.py, src/adapters/llm_router.py, src/api/routes/graph.py | 009, 010, 012, 013, 029 |
| RetrievalEngine | COMP-03 | FR-07, FR-08 | src/services/retrieval_service.py, src/adapters/qdrant_adapter.py | 015, 016 |
| GenerationEngine | COMP-04 | FR-08, FR-12 | src/services/generation_service.py, src/workers/generation_tasks.py | 016, 026 |
| AuthSystem | COMP-05 | FR-09 | src/api/dependencies/auth.py | 018-BE |
| CreditSystem | COMP-06 | FR-10 | src/services/credit_service.py | 023 |
| PrivacyLayer | COMP-07 | FR-11 | src/services/privacy_service.py, src/adapters/presidio_adapter.py | 024, 025 |

---

## COMP-01: IngestionPipeline

**Purpose:** Everything from file upload through indexed chunks.
Owns the full ingestion lifecycle from HTTP request to Qdrant upsert.

**Boundaries:**
- Owns: file validation, MIME detection, SHA-256 dedup, Supabase Storage,
  Docling parsing, chunking, OpenAI embedding, Qdrant upsert,
  content moderation, status transitions, rate limiting
- Does NOT own: entity extraction (COMP-02), retrieval (COMP-03),
  authentication (COMP-05)

**Critical invariants:**
- tenant_id included in every Qdrant payload point
- Source status always transitions PENDING → PROCESSING → INDEXING → COMPLETED
- graph_extraction always enqueued after COMPLETED
- No ARQ retry on failure (no re-raise in except block)

---

## COMP-02: GraphEngine

**Purpose:** Knowledge graph construction, exploration, conflict
detection and resolution, and natural language graph queries.

**Boundaries:**
- Owns: Neo4j writes (Concept MERGE, Memory CREATE), graph API endpoints,
  LLMRouter calls for entity extraction and Cypher generation,
  conflict detection worker, conflict resolution API
- Does NOT own: chunk retrieval for generation (COMP-03),
  authentication (COMP-05)

**Critical invariants:**
- Concept nodes use MERGE, never CREATE (deduplication by {name, tenant_id})
- All Cypher queries pass tenant_id as a parameter — never f-string
- Cypher generation validates output is read-only before executing
- Chunk failures in graph_extraction are logged and skipped — do not abort

---

## COMP-03: RetrievalEngine

**Purpose:** Hybrid retrieval combining Qdrant semantic search with
Neo4j graph-neighbor boosting.

**Boundaries:**
- Owns: hybrid search logic, result ranking, profile-scoped filtering
- Does NOT own: LLM generation (COMP-04), graph writes (COMP-02)

**Critical invariants:**
- All Qdrant queries use _tenant_filter() — never bypass it
- Results always scoped to tenant_id from JWT

---

## COMP-04: GenerationEngine

**Purpose:** LLM-driven document generation and conversational chat,
with PII masking and SSE streaming.

**Boundaries:**
- Owns: meta-document generation, chat session management,
  streaming SSE responses, citation attachment
- Does NOT own: retrieval (COMP-03), privacy/PII masking (COMP-07)

---

## COMP-05: AuthSystem

**Purpose:** JWT validation, Clerk webhook handling, and the
require_user/verify_token_query_param FastAPI dependencies.

**Boundaries:**
- Owns: all JWT decode logic, Clerk JWKS client, webhook handler
- Does NOT own: any business logic — thin gateway only

**Critical invariants:**
- tenant_id always extracted from JWT sub claim
- Never accept user_id from request body or query params

---

## COMP-06: CreditSystem

**Purpose:** Per-operation credit deduction with ledger tracking.

**Boundaries:**
- Owns: credit balance checks, deduction, CreditTransaction writes
- Integrates with all other components that call LLM or storage APIs

---

## COMP-07: PrivacyLayer

**Purpose:** GDPR-compliant cascade deletion and PII masking.

**Boundaries:**
- Owns: cross-store deletion (PostgreSQL, Qdrant, Neo4j, Supabase),
  Presidio PII detection and masking
- Does NOT own: the stores themselves (delegates to adapters)
