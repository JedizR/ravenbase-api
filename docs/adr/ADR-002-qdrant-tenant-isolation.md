# ADR-002: Tenant isolation via payload filtering in Qdrant

**Status:** Accepted
**Date:** 2026-03-25
**Stories:** STORY-003, STORY-005, STORY-009

## Decision
Qdrant uses a single shared collection "ravenbase_chunks".
Tenant isolation is enforced by including tenant_id in every
point payload and calling _tenant_filter() in every query method.

## Rationale
- Collection-per-tenant would require dynamic collection creation
  and complex routing at query time
- Single collection with payload filtering is simpler and scales
  to many tenants without infrastructure changes

## Consequences
- _tenant_filter() MUST be called in every search/scroll/delete
- Any new QdrantAdapter method must enforce tenant isolation
- Tests must verify tenant_id appears in filter conditions
