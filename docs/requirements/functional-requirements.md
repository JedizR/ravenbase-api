# Ravenbase — Functional Requirements

> Agent instruction: This is the authoritative list of what Ravenbase
> must do. Every story references one or more FRs. Every test should
> be traceable to at least one FR acceptance criterion.
> Do not invent behavior not listed here.

## FR-01: Document Ingestion
Users can upload PDF and DOCX files. The system parses, chunks,
embeds, and indexes content asynchronously.

### Acceptance Criteria
- FR-01-AC-1: POST /v1/ingest/upload accepts PDF and DOCX files up to
  200 MB (pro) or 50 MB (free)
- FR-01-AC-2: Duplicate files (same SHA-256 hash per tenant) return
  status="duplicate" without re-processing
- FR-01-AC-3: Unsupported MIME types return 422 INVALID_FILE_TYPE
- FR-01-AC-4: Source record created in PostgreSQL with status PENDING
  → PROCESSING → INDEXING → COMPLETED transitions
- FR-01-AC-5: Chunks upserted to Qdrant with tenant_id in payload
- FR-01-AC-6: Progress published to Redis pub/sub at each status
  transition
- FR-01-AC-7: graph_extraction enqueued after COMPLETED

**Implemented by:** COMP-01 (IngestionPipeline)
**Stories:** STORY-005, STORY-006, STORY-007

---

## FR-02: Text Quick-Capture
Users can ingest plain text directly (no file upload). Same pipeline
as FR-01 but without Docling.

### Acceptance Criteria
- FR-02-AC-1: POST /v1/ingest/text accepts content up to 50,000 chars
- FR-02-AC-2: Content exceeding 50,000 chars returns 422 TEXT_TOO_LONG
- FR-02-AC-3: Source record created with file_type="direct_input"
- FR-02-AC-4: Tags stored in Qdrant payload
- FR-02-AC-5: graph_extraction enqueued after indexing completes

**Implemented by:** COMP-01 (IngestionPipeline)
**Stories:** STORY-008

---

## FR-03: Knowledge Graph Construction
Every ingested source produces Concept and Memory nodes in Neo4j
via entity extraction.

### Acceptance Criteria
- FR-03-AC-1: graph_extraction triggered automatically after FR-01-AC-7
  and FR-02-AC-5
- FR-03-AC-2: Each chunk sent to LLMRouter (Gemini Flash primary,
  Haiku fallback) for entity extraction
- FR-03-AC-3: Concept nodes use MERGE — no duplicates per
  {name, tenant_id}
- FR-03-AC-4: Memory nodes use CREATE — each extraction is unique
- FR-03-AC-5: EXTRACTED_FROM relationship links Memory → Concept
- FR-03-AC-6: RELATES_TO relationship links Concept → Concept
- FR-03-AC-7: All nodes include tenant_id — no cross-tenant leakage
- FR-03-AC-8: Chunks below confidence threshold 0.6 are discarded

**Implemented by:** COMP-02 (GraphEngine)
**Stories:** STORY-009

---

## FR-04: Graph Exploration API
Clients can retrieve the full tenant knowledge graph and neighborhood
subgraphs for visualization.

### Acceptance Criteria
- FR-04-AC-1: GET /v1/graph/nodes returns all Concept and Memory nodes
  for the authenticated tenant
- FR-04-AC-2: Empty graph returns {nodes:[], edges:[]} — never 404
- FR-04-AC-3: GET /v1/graph/neighborhood/{node_id} returns N-hop
  subgraph (default hops=2, max hops=5)
- FR-04-AC-4: tenant_id comes from JWT only — never from query params
- FR-04-AC-5: Optional profile_id filter scopes results to a profile

**Implemented by:** COMP-02 (GraphEngine)
**Stories:** STORY-010

---

## FR-05: Conflict Detection
When new content contradicts existing memories, a Conflict record
is created for human review.

### Acceptance Criteria
- FR-05-AC-1: Qdrant similarity scan identifies candidate contradictions
  above threshold per tenant
- FR-05-AC-2: LLM classifies each candidate as CONTRADICTION,
  DUPLICATE, or NOT_CONFLICT
- FR-05-AC-3: Conflict record created in PostgreSQL with status PENDING
- FR-05-AC-4: Confidence score stored on each Conflict record

**Implemented by:** COMP-02 (GraphEngine)
**Stories:** STORY-012

---

## FR-06: Conflict Resolution
Users can resolve conflicts via three flows: accept new, keep old,
or write custom resolution.

### Acceptance Criteria
- FR-06-AC-1: POST /v1/conflicts/{id}/resolve accepts
  resolution_type in {accept_new, keep_old, custom}
- FR-06-AC-2: Resolution updates Conflict.status and propagates
  changes to Neo4j
- FR-06-AC-3: POST /v1/conflicts/{id}/undo reverts the resolution
- FR-06-AC-4: Resolved conflicts cannot be re-resolved without
  undoing first

**Implemented by:** COMP-02 (GraphEngine)
**Stories:** STORY-013

---

## FR-07: Hybrid Retrieval
The system retrieves relevant memory chunks using combined vector
search (Qdrant) and graph traversal (Neo4j).

### Acceptance Criteria
- FR-07-AC-1: Retrieval combines semantic similarity (Qdrant) with
  graph-neighbor boosting (Neo4j)
- FR-07-AC-2: Results scoped strictly to authenticated tenant_id
- FR-07-AC-3: Optional profile_id filter further scopes results
- FR-07-AC-4: Results ranked by combined relevance score

**Implemented by:** COMP-03 (RetrievalEngine)
**Stories:** STORY-015

---

## FR-08: Meta-Document Generation
The system generates structured documents (resumes, summaries, reports)
by synthesizing retrieved memories via LLM with PII masking.

### Acceptance Criteria
- FR-08-AC-1: POST /v1/generate accepts a natural-language prompt
- FR-08-AC-2: Hybrid retrieval (FR-07) populates context before
  generation
- FR-08-AC-3: PII masked via Presidio before sending to LLM
- FR-08-AC-4: Output streamed via SSE (token by token)
- FR-08-AC-5: MetaDocument record created in PostgreSQL

**Implemented by:** COMP-03 (RetrievalEngine) + COMP-04 (GenerationEngine)
**Stories:** STORY-016

---

## FR-09: Authentication & Authorization
All API endpoints require a valid Clerk JWT. tenant_id is extracted
from the JWT and never accepted from request parameters.

### Acceptance Criteria
- FR-09-AC-1: Every protected endpoint validates JWT via
  require_user dependency
- FR-09-AC-2: tenant_id = JWT sub claim — never from body or query
- FR-09-AC-3: Expired tokens return 403 TOKEN_EXPIRED
- FR-09-AC-4: Invalid tokens return 403 INVALID_TOKEN
- FR-09-AC-5: SSE endpoints use verify_token_query_param (JWT in
  ?token= query param, because EventSource cannot set headers)
- FR-09-AC-6: Clerk webhook creates User record in PostgreSQL on
  first sign-up

**Implemented by:** COMP-05 (AuthSystem)
**Stories:** STORY-018

---

## FR-10: Credits System
Every LLM and embedding operation deducts credits from the user
balance. Operations fail with 402 when balance is insufficient.

### Acceptance Criteria
- FR-10-AC-1: Credits deducted atomically per operation type
- FR-10-AC-2: CreditTransaction row written for every deduction
- FR-10-AC-3: 402 INSUFFICIENT_CREDITS returned when balance < cost
- FR-10-AC-4: Free tier: 200 credits on signup

**Implemented by:** COMP-06 (CreditSystem)
**Stories:** STORY-023

---

## FR-11: Privacy & PII Protection
User data can be fully deleted across all stores. PII is masked
before LLM processing.

### Acceptance Criteria
- FR-11-AC-1: DELETE /v1/account triggers cascade deletion across
  PostgreSQL, Qdrant, Neo4j, and Supabase Storage
- FR-11-AC-2: Deletion completes within 60 seconds for typical accounts
- FR-11-AC-3: Presidio masks PII categories (email, phone, name,
  financial) before LLM calls in FR-08
- FR-11-AC-4: Presidio configuration is consistent across all
  generation endpoints

**Implemented by:** COMP-07 (PrivacyLayer)
**Stories:** STORY-024, STORY-025

---

## FR-12: Conversational Memory Chat
Users can have multi-turn conversations with their knowledge base,
receiving answers with source citations.

### Acceptance Criteria
- FR-12-AC-1: POST /v1/chat/sessions creates a new session
- FR-12-AC-2: POST /v1/chat/sessions/{id}/message streams response
  via SSE with citations
- FR-12-AC-3: Citations reference specific Memory node IDs
- FR-12-AC-4: Multi-turn context preserved within session
- FR-12-AC-5: Credits deducted per message

**Implemented by:** COMP-04 (GenerationEngine)
**Stories:** STORY-026

---

## FR-13: Natural Language Graph Queries
Users can query the knowledge graph using plain English, which is
translated to Cypher by LLMRouter.

### Acceptance Criteria
- FR-13-AC-1: POST /v1/graph/query accepts natural language input
- FR-13-AC-2: LLMRouter generates safe read-only Cypher
- FR-13-AC-3: Generated Cypher validated — write operations rejected
- FR-13-AC-4: Query results returned as GraphResponse

**Implemented by:** COMP-02 (GraphEngine)
**Stories:** STORY-029
