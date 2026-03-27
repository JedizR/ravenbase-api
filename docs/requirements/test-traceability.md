# Test Traceability Matrix

> Agent instruction: When you write a new test, add a row to this table.
> When you implement a new FR acceptance criterion, add the AC here even
> if no test exists yet (mark as UNTESTED). This table is the answer to
> "which test proves FR-XX-AC-Y?".

| FR-AC | Description | Test File | Test Function | Type | Story |
|---|---|---|---|---|---|
| FR-01-AC-1 | Upload accepts PDF/DOCX | tests/integration/api/test_ingest_upload.py | test_ingest_upload_valid_pdf_returns_202 | integration | STORY-005 |
| FR-01-AC-2 | Duplicate returns status=duplicate | tests/integration/api/test_ingest_upload.py | test_ingest_upload_duplicate_returns_duplicate_status | integration | STORY-005 |
| FR-01-AC-3 | Invalid MIME → 422 | tests/integration/api/test_ingest_upload.py | test_ingest_upload_invalid_mime_returns_422 | integration | STORY-005 |
| FR-01-AC-5 | Chunks upserted to Qdrant | tests/integration/workers/test_ingestion_tasks.py | test_parse_document_happy_path | integration | STORY-006 |
| FR-01-AC-6 | Progress published to Redis | tests/integration/workers/test_ingestion_tasks.py | test_parse_document_happy_path | integration | STORY-006 |
| FR-01-AC-7 | graph_extraction enqueued | tests/integration/workers/test_ingestion_tasks.py | test_parse_document_happy_path | integration | STORY-006 |
| FR-02-AC-1 | Text accepted up to 50k | tests/integration/api/test_ingest_text.py | test_ingest_text_happy_path_returns_202 | integration | STORY-008 |
| FR-02-AC-2 | >50k returns 422 | tests/integration/api/test_ingest_text.py | test_ingest_text_too_long_returns_422 | integration | STORY-008 |
| FR-03-AC-2 | LLM called per chunk | tests/unit/services/test_graph_service.py | test_extract_and_write_calls_llm_per_chunk | unit | STORY-009 |
| FR-03-AC-3 | Concept nodes use MERGE | tests/unit/services/test_graph_service.py | test_concept_writes_use_merge_not_create | unit | STORY-009 |
| FR-03-AC-7 | All nodes include tenant_id | tests/unit/services/test_graph_service.py | test_all_neo4j_calls_include_tenant_id | unit | STORY-009 |
| FR-03-AC-8 | Low confidence filtered | tests/unit/services/test_graph_service.py | test_extract_and_write_filters_low_confidence_entities | unit | STORY-009 |
| FR-04-AC-1 | GET /nodes returns graph | tests/integration/api/test_graph_endpoints.py | test_get_nodes_returns_200_with_graph_shape | integration | STORY-010 |
| FR-04-AC-2 | Empty graph → 200 not 404 | tests/integration/api/test_graph_endpoints.py | test_get_nodes_empty_graph_returns_empty_arrays | integration | STORY-010 |
| FR-04-AC-3 | Neighborhood returns subgraph | tests/integration/api/test_graph_endpoints.py | test_get_neighborhood_returns_200 | integration | STORY-010 |
| FR-04-AC-4 | tenant_id from JWT only | tests/integration/api/test_graph_endpoints.py | test_get_nodes_no_auth_returns_401 | integration | STORY-010 |
