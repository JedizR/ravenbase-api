# Test Traceability Matrix

> Agent instruction: When you write a new test, add a row to this table.
> When you implement a new FR acceptance criterion, add the AC here even
> if no test exists yet (mark as UNTESTED). This table is the answer to
> "which test proves FR-XX-AC-Y?".

| FR-AC | Description | Test File | Test Function | Type | Story |
|---|---|---|---|---|---|
| FR-01-AC-1 | Upload accepts PDF/DOCX | tests/integration/api/test_ingest_upload.py | test_upload_valid_pdf_returns_202_queued | integration | STORY-005 |
| FR-01-AC-2 | Duplicate returns status=duplicate | tests/integration/api/test_ingest_upload.py | test_upload_duplicate_returns_existing_source_id | integration | STORY-005 |
| FR-01-AC-3 | Invalid MIME → 422 | tests/integration/api/test_ingest_upload.py | test_upload_invalid_mime_returns_422 | integration | STORY-005 |
| FR-01-AC-4 | Source status transitions PENDING→COMPLETED | UNTESTED | UNTESTED | — | STORY-005 |
| FR-01-AC-5 | Chunks upserted to Qdrant | tests/integration/workers/test_ingestion_tasks.py | test_parse_document_happy_path | integration | STORY-006 |
| FR-01-AC-6 | Progress published to Redis | tests/integration/workers/test_ingestion_tasks.py | test_parse_document_happy_path | integration | STORY-006 |
| FR-01-AC-7 | graph_extraction enqueued | tests/integration/workers/test_ingestion_tasks.py | test_parse_document_happy_path | integration | STORY-006 |
| FR-02-AC-1 | Text accepted up to 50k | tests/integration/api/test_ingest_text.py | test_ingest_text_happy_path_returns_202 | integration | STORY-008 |
| FR-02-AC-2 | >50k returns 422 | tests/integration/api/test_ingest_text.py | test_ingest_text_too_long_returns_422 | integration | STORY-008 |
| FR-02-AC-3 | Source created with file_type=direct_input | UNTESTED | UNTESTED | — | STORY-008 |
| FR-02-AC-4 | Tags stored in Qdrant payload | UNTESTED | UNTESTED | — | STORY-008 |
| FR-02-AC-5 | graph_extraction enqueued after text indexing | UNTESTED | UNTESTED | — | STORY-008 |
| FR-03-AC-1 | graph_extraction triggered after FR-01-AC-7 and FR-02-AC-5 | UNTESTED | UNTESTED | — | STORY-009 |
| FR-03-AC-2 | LLM called per chunk | tests/unit/services/test_graph_service.py | test_extract_and_write_calls_llm_per_chunk | unit | STORY-009 |
| FR-03-AC-3 | Concept nodes use MERGE | tests/unit/services/test_graph_service.py | test_concept_writes_use_merge_not_create | unit | STORY-009 |
| FR-03-AC-4 | Memory nodes use CREATE | UNTESTED | UNTESTED | — | STORY-009 |
| FR-03-AC-5 | EXTRACTED_FROM relationship written | UNTESTED | UNTESTED | — | STORY-009 |
| FR-03-AC-6 | RELATES_TO relationship written | UNTESTED | UNTESTED | — | STORY-009 |
| FR-03-AC-7 | All nodes include tenant_id | tests/unit/services/test_graph_service.py | test_all_neo4j_calls_include_tenant_id | unit | STORY-009 |
| FR-03-AC-8 | Low confidence filtered | tests/unit/services/test_graph_service.py | test_extract_and_write_filters_low_confidence_entities | unit | STORY-009 |
| FR-04-AC-1 | GET /nodes returns graph | tests/integration/api/test_graph_endpoints.py | test_get_nodes_returns_200_with_graph_shape | integration | STORY-010 |
| FR-04-AC-2 | Empty graph → 200 not 404 | tests/integration/api/test_graph_endpoints.py | test_get_nodes_empty_graph_returns_empty_arrays | integration | STORY-010 |
| FR-04-AC-3 | Neighborhood returns subgraph | tests/integration/api/test_graph_endpoints.py | test_get_neighborhood_returns_200 | integration | STORY-010 |
| FR-04-AC-4 | tenant_id from JWT only | tests/integration/api/test_graph_endpoints.py | test_get_nodes_no_auth_returns_401 | integration | STORY-010 |
| FR-04-AC-5 | profile_id filter scopes results | UNTESTED | UNTESTED | — | STORY-010 |
| FR-05-AC-1 | Qdrant scan finds contradiction candidates | UNTESTED | UNTESTED | — | STORY-012 |
| FR-05-AC-2 | LLM classifies CONTRADICTION/DUPLICATE/NOT_CONFLICT | UNTESTED | UNTESTED | — | STORY-012 |
| FR-05-AC-3 | Conflict record created with status PENDING | UNTESTED | UNTESTED | — | STORY-012 |
| FR-05-AC-4 | Confidence score stored on Conflict record | UNTESTED | UNTESTED | — | STORY-012 |
| FR-06-AC-1 | POST /conflicts/{id}/resolve accepts resolution_type | UNTESTED | UNTESTED | — | STORY-013 |
| FR-06-AC-2 | Resolution propagates changes to Neo4j | UNTESTED | UNTESTED | — | STORY-013 |
| FR-06-AC-3 | POST /conflicts/{id}/undo reverts resolution | UNTESTED | UNTESTED | — | STORY-013 |
| FR-06-AC-4 | Resolved conflicts cannot be re-resolved without undo | UNTESTED | UNTESTED | — | STORY-013 |
| FR-07-AC-1 | Retrieval combines Qdrant + Neo4j graph-neighbor boost | UNTESTED | UNTESTED | — | STORY-015 |
| FR-07-AC-2 | Results scoped to authenticated tenant_id | UNTESTED | UNTESTED | — | STORY-015 |
| FR-07-AC-3 | profile_id filter further scopes results | UNTESTED | UNTESTED | — | STORY-015 |
| FR-07-AC-4 | Results ranked by combined relevance score | UNTESTED | UNTESTED | — | STORY-015 |
| FR-08-AC-1 | POST /v1/generate accepts natural-language prompt | UNTESTED | UNTESTED | — | STORY-016 |
| FR-08-AC-2 | Hybrid retrieval populates context before generation | UNTESTED | UNTESTED | — | STORY-016 |
| FR-08-AC-3 | PII masked via Presidio before LLM call | UNTESTED | UNTESTED | — | STORY-016 |
| FR-08-AC-4 | Output streamed via SSE | UNTESTED | UNTESTED | — | STORY-016 |
| FR-08-AC-5 | MetaDocument record created in PostgreSQL | UNTESTED | UNTESTED | — | STORY-016 |
| FR-09-AC-1 | Every protected endpoint validates JWT | UNTESTED | UNTESTED | — | STORY-018 |
| FR-09-AC-2 | tenant_id = JWT sub claim only | UNTESTED | UNTESTED | — | STORY-018 |
| FR-09-AC-3 | Expired tokens return 403 TOKEN_EXPIRED | UNTESTED | UNTESTED | — | STORY-018 |
| FR-09-AC-4 | Invalid tokens return 403 INVALID_TOKEN | UNTESTED | UNTESTED | — | STORY-018 |
| FR-09-AC-5 | SSE endpoints use ?token= query param | UNTESTED | UNTESTED | — | STORY-018 |
| FR-09-AC-6 | Clerk webhook creates User record on first sign-up | UNTESTED | UNTESTED | — | STORY-018 |
| FR-10-AC-1 | Credits deducted atomically per operation | UNTESTED | UNTESTED | — | STORY-023 |
| FR-10-AC-2 | CreditTransaction row written per deduction | UNTESTED | UNTESTED | — | STORY-023 |
| FR-10-AC-3 | 402 INSUFFICIENT_CREDITS when balance < cost | UNTESTED | UNTESTED | — | STORY-023 |
| FR-10-AC-4 | Free tier: 200 credits on signup | UNTESTED | UNTESTED | — | STORY-023 |
| FR-11-AC-1 | DELETE /v1/account cascades across all stores | UNTESTED | UNTESTED | — | STORY-024 |
| FR-11-AC-2 | Full deletion completes within 60 seconds | UNTESTED | UNTESTED | — | STORY-024 |
| FR-11-AC-3 | Presidio masks PII before LLM calls | UNTESTED | UNTESTED | — | STORY-025 |
| FR-11-AC-4 | Presidio config consistent across all generation endpoints | UNTESTED | UNTESTED | — | STORY-025 |
| FR-12-AC-1 | POST /v1/chat/sessions creates new session | UNTESTED | UNTESTED | — | STORY-026 |
| FR-12-AC-2 | POST /v1/chat/sessions/{id}/message streams SSE with citations | UNTESTED | UNTESTED | — | STORY-026 |
| FR-12-AC-3 | Citations reference specific Memory node IDs | UNTESTED | UNTESTED | — | STORY-026 |
| FR-12-AC-4 | Multi-turn context preserved within session | UNTESTED | UNTESTED | — | STORY-026 |
| FR-12-AC-5 | Credits deducted per chat message | UNTESTED | UNTESTED | — | STORY-026 |
| FR-13-AC-1 | POST /v1/graph/query accepts natural language input | UNTESTED | UNTESTED | — | STORY-029 |
| FR-13-AC-2 | LLMRouter generates safe read-only Cypher | UNTESTED | UNTESTED | — | STORY-029 |
| FR-13-AC-3 | Generated Cypher validated — write operations rejected | UNTESTED | UNTESTED | — | STORY-029 |
| FR-13-AC-4 | Query results returned as GraphResponse | UNTESTED | UNTESTED | — | STORY-029 |
