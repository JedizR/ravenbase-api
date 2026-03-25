# Feature Spec — F2: Knowledge Graph Layer

> **Stories:** STORY-009, STORY-010

## Overview
Dual-write architecture: all ingested content → Qdrant (semantic search) AND → Neo4j (temporal/relational reasoning).

## Node Types
| Label | Key Properties | Purpose |
|---|---|---|
| `User` | user_id, email | Root tenant node |
| `SystemProfile` | profile_id, tenant_id, name | Context scope |
| `Memory` | memory_id, tenant_id, content, is_valid | Canonical fact |
| `Concept` | concept_id, tenant_id, name, type | Extracted entity |
| `Source` | source_id, tenant_id, filename | Origin document |
| `Conflict` | conflict_id, tenant_id, status | Pending inbox item |
| `MetaDocument` | doc_id, tenant_id, title | Synthesis output |

## Relationship Types
| Type | From → To | Properties |
|---|---|---|
| `EXTRACTED_FROM` | Memory → Source | chunk_id |
| `RELATES_TO` | Memory → Concept | weight, context |
| `CONTRADICTS` | Memory → Memory | conflict_id |
| `SUPERSEDES` | Memory → Memory | resolved_at |
| `CONTAINS` | MetaDocument → Memory | relevance_score |
| `TEMPORAL_LINK` | Concept → Concept | direction, year |

## Acceptance Criteria
- [ ] All nodes include `tenant_id` (enforced in adapter — no exceptions)
- [ ] Concept deduplication: MERGE on (name, tenant_id) — never create duplicates
- [ ] Graph queries return results in < 500ms for 50K nodes
- [ ] Empty graph (new user): returns empty collections, not errors
