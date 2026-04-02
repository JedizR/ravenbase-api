# COMP-02: GraphEngine

> **Component ID:** BE-COMP-02
> **Epic:** EPIC-03 — Knowledge Graph Layer, EPIC-04 — Conflict Detection & Memory Inbox, EPIC-09 — Memory Intelligence
> **Stories:** STORY-009, STORY-010, STORY-011, STORY-012, STORY-013, STORY-014, STORY-029, STORY-030
> **Type:** Cross-repo (Backend + Frontend)

---

## Purpose

The GraphEngine owns knowledge graph construction, exploration, conflict detection and resolution, and natural language graph queries. It transforms raw ingested content into a living, queryable knowledge graph stored in Neo4j, surfaces contradictions to users via the Memory Inbox, and enables natural language exploration of graph data via Text-to-Cypher.

---

## User Journey

**Graph is built automatically (no user action required):**
1. User uploads a file → IngestionPipeline completes → automatically enqueues `graph_extraction` ARQ task
2. LLM extracts entities, memories, relationships from chunks → writes to Neo4j
3. After graph write, `scan_for_conflicts` task runs automatically
4. If contradictions found → `Conflict` records created → sidebar badge increments

**User browses graph (FE-COMP-06):**
- `/graph` → `GET /v1/graph/nodes` → Cytoscape.js renders
- Click node → `GET /v1/graph/neighborhood/{id}` → detail panel
- Type NL query → `POST /v1/graph/query` → amber-highlighted subgraph (costs 2 credits)

**User resolves conflicts (FE-COMP-05):**
- `/inbox` → `GET /v1/conflicts?status=pending` → keyboard triage
- `J/K/Enter/Backspace` → `POST /v1/conflicts/{id}/resolve` → `ACCEPT_NEW | KEEP_OLD | CUSTOM`
- 30-second undo window → `POST /v1/conflicts/{id}/undo`

---

## Admin Bypass

NL graph queries (`POST /v1/graph/query`) cost 2 credits per call.

Admin users (identified by `ADMIN_USER_IDS` env var): `CreditService.check_or_raise()` returns early → queries run for free. Frontend: no change needed — sidebar shows `◆ ADMIN_ACCESS` instead of credit count.

All other graph operations (browse, conflict triage, resolution) are free — no bypass needed.

---

## Known Bugs / Current State

**BUG-018 (HIGH):** Date range filter UI exists in Graph Explorer but `filteredNodes` never applies it.
- **Root cause:** `app/(dashboard)/graph/GraphPageClient.tsx:38-70` — `dateRange.from/to` collected but ignored in `filteredNodes` useMemo.
- **Fix:** Add date filtering to `filteredNodes` — see FE-COMP-06 for exact fix.
- **Story:** STORY-039

**Cypher safety invariants (already implemented, must not regress):**
- `tenant_id` ALWAYS a Neo4j query parameter, NEVER string-interpolated
- Generated Cypher rejected if it contains any write keyword (`CREATE`, `MERGE`, `SET`, `DELETE`)
- `limit` capped at 50 in code — never from LLM output

---

## Cross-references

- `FE-COMP-05-MemoryInbox.md` — keyboard-first conflict resolution UI
- `FE-COMP-06-GraphExplorer.md` — Cytoscape.js visualization, NL query UI
- `BE-COMP-06-CreditSystem.md` — 2 credit cost for NL queries
- `docs/architecture/02-database-schema.md` — Neo4j node/edge types
- `docs/architecture/03-api-contract.md` — graph and conflict endpoints
- `docs/components/REFACTOR_PLAN.md` — BUG-018 fix details

---

## Goal

The GraphEngine owns knowledge graph construction, exploration, conflict detection and resolution, and natural language graph queries. It transforms raw ingested content into a living, queryable knowledge graph stored in Neo4j, surfaces contradictions to users via the Memory Inbox, and enables natural language exploration of graph data.

---

## Product Requirements

1. **Entity Extraction:** After ingestion completes (`COMPLETED` status), `graph_extraction` ARQ job is automatically enqueued. Each document chunk is sent to `LLMRouter().complete("entity_extraction")` using Gemini 2.5 Flash primary with Claude Haiku automatic fallback.

2. **Structured Output Extraction:** The LLM extraction prompt produces: `{entities: [{name, type, confidence}], memories: [{content, confidence}], relationships: [{from, to, type}]}`. Entities with confidence < 0.6 are discarded. Maximum 10 entities, 5 memories, 5 relationships per chunk.

3. **Neo4j Concept MERGE:** Concept nodes use `MERGE` on `{name, tenant_id}` — never `CREATE`. This deduplicates concepts across chunks so "Python" mentioned in 20 chunks = 1 Concept node. All nodes include `tenant_id` property.

4. **Neo4j Memory CREATE:** Memory nodes use `CREATE` — each extraction is unique. Linked to Concept nodes via `EXTRACTED_FROM` edges and to Source via `source_id` property.

5. **Concept-to-Concept RELATES_TO:** Relationships between concepts are written to Neo4j. The extraction prompt supports: `USES`, `WORKED_ON`, `LED`, `KNOWS`, `DECIDED` relationship types.

6. **Graph API — Nodes Endpoint:** `GET /v1/graph/nodes?profile_id=&node_types=&limit=200` returns `{nodes: [{id, label, type, properties, memory_count}], edges: [{source, target, type, properties}]}`. Empty graph returns `{nodes: [], edges: []}` — never 404.

7. **Graph API — Neighborhood Endpoint:** `GET /v1/graph/neighborhood/{node_id}?hops=2&limit=50` returns N-hop subgraph centered on that node. Default hops=2, max hops=5.

8. **Tenant Isolation:** All Neo4j queries filter by `tenant_id` from JWT only — never from query params or request body. tenant_id is ALWAYS a Neo4j query parameter, NEVER string-interpolated.

9. **Conflict Detection — Qdrant Scan:** After `write_graph_nodes` completes, `scan_for_conflicts` task runs. Qdrant cosine similarity scan finds embeddings > 0.87 threshold vs new memory embeddings. All candidates filtered by `tenant_id` and `is_valid=true`.

10. **Conflict Detection — LLM Classification:** Candidate pairs sent to `LLMRouter().complete("conflict_classification")`. Returns `{classification: "CONTRADICTION|UPDATE|COMPLEMENT|DUPLICATE", confidence: 0.0-1.0, reasoning: string}`. Skip pairs with confidence < 0.70.

11. **Temporal + Authority Weighting:** For CONTRADICTION or UPDATE: older memory is incumbent, newer is challenger. Auto-resolve if `challenger_source.authority_weight - incumbent_source.authority_weight >= 3`. Set `status=auto_resolved`, mark old `is_valid=false`.

12. **Conflict Record Creation:** CONTRADICTION or UPDATE with confidence >= 0.70: create `Conflict` record in PostgreSQL with both memory content snapshots. Maximum 5 conflicts per ingestion batch.

13. **CONTRADICTS Neo4j Edge:** When a Conflict is created, write a `CONTRADICTS` edge between the two Memory nodes in Neo4j. COMPLEMENT classifications write a `TEMPORAL_LINK` edge instead (no Conflict record).

14. **Conflict Resolution API — Accept New:** `POST /v1/conflicts/{id}/resolve` with `action=ACCEPT_NEW`: marks new memory `is_valid=true`, old `is_valid=false`, creates `SUPERSEDES` Neo4j edge.

15. **Conflict Resolution API — Keep Old:** `POST /v1/conflicts/{id}/resolve` with `action=KEEP_OLD`: marks conflict resolved, no graph changes.

16. **Conflict Resolution API — Custom:** `POST /v1/conflicts/{id}/resolve` with `action=CUSTOM + custom_text`: sends text to Claude Haiku to generate graph mutation commands, applies them atomically.

17. **Undo Window:** `POST /v1/conflicts/{id}/undo` reverses resolution if within 30-second window from `resolved_at`. Returns `409 Conflict` after window expires.

18. **Redis Pub/Sub Notification:** After Conflict record is committed to PostgreSQL, publish to Redis channel `conflict:new:{tenant_id}` for SSE inbox subscribers.

19. **Graph Explorer — Cytoscape.js:** `GET /v1/graph/nodes` renders a force-directed graph using Cytoscape.js with `cytoscape-fcose` layout. Node colors: concept=`#2d4a3e` (primary green), memory=`#e8ebe6` (secondary), source=`#a8c4b2` (accent), conflict=`#ffc00d` (amber, pulsing).

20. **Graph Explorer — Node Click:** Clicking a node calls `GET /v1/graph/neighborhood/{node_id}?hops=2` and opens a right-side detail panel showing node properties and linked memories.

21. **Graph Explorer — Filters:** Profile filter, node type filter (checkboxes), date range filter in side panel. All filters update the Cytoscape view.

22. **Graph Explorer — Mobile:** On mobile (< 768px): gracefully degrades to a searchable list of concepts, not the force graph.

23. **Memory Inbox — Binary Triage Flow:** J/K cycles through conflict cards, Enter accepts AI resolution, Backspace rejects (keep old). All with < 200ms optimistic UI update.

24. **Memory Inbox — Conversational Flow:** Press `C` on a conflict card to expand inline chat. User types custom text, presses Enter → calls `POST /v1/conflicts/{id}/resolve` with `action=CUSTOM`.

25. **Memory Inbox — Auto-Resolved Flow:** Toast notification with 30-second countdown: "Updated [X]. Undo?". Clicking Undo calls `POST /v1/conflicts/{id}/undo`.

26. **Memory Inbox — Optimistic UI:** Conflict card animates out immediately on resolution. API call happens in background. On API failure: card animates back in with error toast.

27. **Natural Language Graph Query Backend:** `POST /v1/graph/query` accepts `{query, profile_id?, limit?}` and returns `{cypher, results: {nodes, edges}, explanation, query_time_ms}`. LLMRouter generates Cypher via Gemini 2.5 Flash.

28. **Cypher Safety Validation:** Generated Cypher is validated before execution. Reject if it contains `CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DROP`. Returns `422 UNSAFE_QUERY` if rejected. tenant_id is ALWAYS injected by the service, never by LLM output.

29. **Cypher Generation Limit:** `limit` defaults to 20, max 50. Limit is capped in code — never trust LLM-generated LIMIT values.

30. **NL Query — 2 Credits:** Natural language graph queries cost 2 credits per query. Returns `402` if insufficient credits before LLM call.

31. **NL Query Frontend — Query Bar:** Graph Explorer shows query bar above filters: `[Ask your graph anything...] [Search]`. Example query chips when empty: "Show my Python projects", "Skills since 2023", "What did I decide about databases?".

32. **NL Query Frontend — Highlighting:** Submitting a query highlights matching nodes amber (`#ffc00d`) in Cytoscape graph. Results panel slides in from right showing matched Memory nodes as cards.

33. **NL Query Frontend — Cypher Transparency:** Expandable "Show Cypher" section below results shows the generated query for power users.

34. **Conflict Count Badge:** Sidebar nav icon shows pending conflict count badge. Updates in real-time via polling or SSE.

---

## Criteria and Tests

| Criterion | Test |
|---|---|
| Entity extraction runs after ingestion completes | Upload PDF → check Redis queue → `graph_extraction` job exists |
| Concept nodes deduplicated via MERGE | Upload 2 docs mentioning "Python" → Neo4j has 1 Concept node for "Python" |
| Memory nodes unique per extraction | Upload doc with 20 chunks → Neo4j has 20 Memory nodes |
| `GET /v1/graph/nodes` returns empty for new user | New user calls endpoint → `{nodes: [], edges: []}` |
| `GET /v1/graph/neighborhood/{node_id}` returns N-hop subgraph | Click node in UI → subgraph loads centered on that node |
| Conflict detection finds contradictory memories | Upload "I use Python" then "I stopped using Python" → conflict created |
| Qdrant scan is tenant-scoped | User A's memories never match User B's memories in Qdrant scan |
| Auto-resolution triggers at authority delta >= 3 | Challenger source weight - incumbent weight >= 3 → auto_resolved |
| Max 5 conflicts per batch | Upload 50-chunk doc with 10 potential conflicts → only 5 Conflict records |
| `POST /v1/conflicts/{id}/resolve` ACCEPT_NEW works | Call with action=ACCEPT_NEW → SUPERSEDES edge in Neo4j, old is_valid=false |
| `POST /v1/conflicts/{id}/undo` works within 30s | Undo within window → Neo4j state reverted |
| `POST /v1/conflicts/{id}/undo` returns 409 after 30s | Undo after 30s → 409 Conflict |
| Graph Explorer renders Cytoscape graph | Navigate to /graph → force-directed graph visible |
| Conflict nodes pulse amber | Conflict exists → amber pulsing animation visible |
| Memory Inbox J/K navigation works | Press J → next card selected, K → previous |
| Memory Inbox optimistic UI reverts on error | Disconnect network mid-resolve → card animates back in |
| NL query returns highlighted nodes | Query "Python projects" → amber-highlighted nodes in graph |
| NL query safety rejects write Cypher | Query "delete all my memories" → 422 UNSAFE_QUERY |
| Empty NL query results shows empty state | Query that matches nothing → "No memories found" message |

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-009](../stories/EPIC-03-graph/STORY-009.md) | Entity Extraction + Neo4j Writer | Backend | Gemini Flash via LLMRouter → entity extraction → Neo4j MERGE/CREATE |
| [STORY-010](../stories/EPIC-03-graph/STORY-010.md) | Graph API Endpoints | Backend | `GET /v1/graph/nodes`, `GET /v1/graph/neighborhood/{node_id}` |
| [STORY-011](../stories/EPIC-03-graph/STORY-011.md) | Graph Explorer UI | Frontend | Cytoscape.js force-directed graph, node click panel, filters |
| [STORY-012](../stories/EPIC-04-conflict/STORY-012.md) | Conflict Detection Worker | Backend | Qdrant scan + LLM classify + Conflict record creation |
| [STORY-013](../stories/EPIC-04-conflict/STORY-013.md) | Conflict API (List, Resolve, Undo) | Backend | `GET /v1/conflicts`, `POST /v1/conflicts/{id}/resolve`, `POST /v1/conflicts/{id}/undo` |
| [STORY-014](../stories/EPIC-04-conflict/STORY-014.md) | Memory Inbox UI | Frontend | Keyboard-navigable inbox, 3 resolution flows, optimistic UI |
| [STORY-029](../stories/EPIC-09-memory-intelligence/STORY-029.md) | NL Graph Query — Backend | Backend | `POST /v1/graph/query`, Text-to-Cypher, safety validation |
| [STORY-030](../stories/EPIC-09-memory-intelligence/STORY-030.md) | NL Graph Query — Frontend | Frontend | Query bar, amber highlighting, results panel, Cypher reveal |

---

## Subcomponents

The GraphEngine decomposes into 8 subcomponents, each matching 1-2 stories.

---

### SUBCOMP-02A: Entity Extraction Worker

**Stories:** STORY-009
**Files:** `src/workers/graph_tasks.py`, `src/services/graph_service.py`, `src/adapters/neo4j_adapter.py`, `src/adapters/llm_router.py`

#### Details
The `graph_extraction` ARQ task is automatically enqueued after ingestion completes (`COMPLETED` status). It extracts entities, memories, and relationships from each chunk using `LLMRouter().complete("entity_extraction")`, then writes Concept and Memory nodes to Neo4j. Concept nodes use `MERGE` to deduplicate across chunks. Memory nodes use `CREATE` so each extraction is unique.

#### Criteria of Done
- [ ] `graph_extraction` job enqueued automatically after ingestion `COMPLETED`
- [ ] `LLMRouter().complete("entity_extraction")` called per chunk — routes to Gemini 2.5 Flash with Haiku fallback
- [ ] Extraction prompt produces structured JSON: `{entities, memories, relationships}`
- [ ] Confidence < 0.6 entities discarded
- [ ] Concept nodes use `MERGE` on `{name, tenant_id}` — no duplicates
- [ ] Memory nodes use `CREATE` — each extraction unique
- [ ] `EXTRACTED_FROM` edges link Memory → Concept
- [ ] `RELATES_TO` edges link Concept → Concept
- [ ] All nodes include `tenant_id` property
- [ ] Token usage logged to structlog via LLMRouter metadata callback
- [ ] 50-page document: extraction completes within 3 minutes
- [ ] Failed chunk: log + skip, do NOT fail entire task

#### Checklist
- [ ] Docling import inside function body (`# noqa: PLC0415`)
- [ ] `LLMRouter` called with `response_format={"type":"json_object"}`
- [ ] MERGE key includes both `name` AND `tenant_id`
- [ ] Memory CREATE includes `tenant_id`, `source_id`, `created_at`
- [ ] Neo4j write in `write_graph_nodes` task uses transaction
- [ ] Source status updated to `completed` after graph nodes written
- [ ] `publish_progress()` called at extraction milestones
- [ ] `enqueue_job("scan_for_conflicts", ...)` called after `write_graph_nodes` completes

#### Testing
```bash
# Verify Neo4j nodes after ingestion:
# Open Neo4j Browser at http://localhost:7474
MATCH (n) WHERE n.tenant_id = "your-tenant-id" RETURN n LIMIT 25
# Expected: Concept nodes with deduplicated names, Memory nodes with EXTRACTED_FROM edges

# Check ARQ job queue:
redis-cli LRANGE arq:queue:default 0 -1
# Expected: graph_extraction job exists after source COMPLETED

# Conflict detection after extraction:
# Upload conflicting docs, then:
MATCH (m1:Memory)-[:CONTRADICTS]-(m2:Memory) RETURN m1, m2
# Expected: CONTRADICTS edge between conflicting memories
```

---

### SUBCOMP-02B: Graph API Endpoints

**Stories:** STORY-010
**Files:** `src/api/routes/graph.py`, `src/services/graph_service.py`, `src/schemas/graph.py`, `tests/integration/api/test_graph_endpoints.py`

#### Details
The Graph API provides two REST endpoints for the Graph Explorer UI: `GET /v1/graph/nodes` returns all Concept and Memory nodes for the authenticated tenant, and `GET /v1/graph/neighborhood/{node_id}` returns an N-hop subgraph centered on a specific node. All queries are tenant-scoped via JWT. Empty graphs return `[]` not 404.

#### Criteria of Done
- [ ] `GET /v1/graph/nodes?profile_id=&node_types=&limit=200` returns `{nodes, edges}`
- [ ] Response shape: `{nodes: [{id, label, type, properties, memory_count}], edges: [{source, target, type, properties}]}`
- [ ] `GET /v1/graph/neighborhood/{node_id}?hops=2&limit=50` returns N-hop subgraph
- [ ] tenant_id comes exclusively from `require_user` JWT — never from query params
- [ ] Optional `profile_id` filter scopes results via `HAS_MEMORY` edges
- [ ] Empty graph returns `{nodes: [], edges: []}` — never 404
- [ ] Response time < 500ms for graphs up to 500 nodes

#### Checklist
- [ ] `GraphNode`, `GraphEdge`, `GraphResponse` Pydantic schemas in `src/schemas/graph.py`
- [ ] Route calls `graph_service.get_nodes_for_explorer()` — not `neo4j_adapter` directly
- [ ] `tenant_id` injected as Cypher parameter, not f-string interpolated
- [ ] Profile filter: `OPTIONAL MATCH` pattern in Cypher
- [ ] Neighborhood query includes `tenant_id` in WHERE clause even when filtering by `node_id`
- [ ] Integration tests with two different tenant_ids verify isolation

#### Testing
```bash
# Happy path — empty graph:
curl -X GET "http://localhost:8000/v1/graph/nodes" \
  -H "Authorization: Bearer TOKEN"
# Expected: {"nodes": [], "edges": []}

# With profile filter:
curl -X GET "http://localhost:8000/v1/graph/nodes?profile_id=UUID&limit=50" \
  -H "Authorization: Bearer TOKEN"
# Expected: nodes linked to profile via HAS_MEMORY edges

# Neighborhood:
curl -X GET "http://localhost:8000/v1/graph/neighborhood/{node_id}?hops=2" \
  -H "Authorization: Bearer TOKEN"
# Expected: subgraph centered on node_id

# Tenant isolation test:
# Create nodes for tenant A, query as tenant B → verify no cross-tenant data
```

---

### SUBCOMP-02C: Graph Explorer UI

**Stories:** STORY-011
**Files:** `components/domain/GraphExplorer.tsx`, `components/domain/GraphNodePanel.tsx`, `components/domain/GraphFilters.tsx`, `app/(dashboard)/graph/page.tsx`

#### Details
The Graph Explorer renders the knowledge graph as a force-directed visualization using Cytoscape.js with `cytoscape-fcose` layout. It loads all nodes via `GET /v1/graph/nodes` and allows users to click any node to see its neighborhood. Node types have distinct brand-consistent colors. On mobile (< 768px), it degrades gracefully to a searchable concept list.

#### Criteria of Done
- [ ] Force-directed graph renders with Cytoscape.js + `cytoscape-fcose`
- [ ] Node colors: concept=`#2d4a3e` (primary green), memory=`#e8ebe6` (secondary), source=`#a8c4b2` (accent), conflict=`#ffc00d` (amber, pulsing)
- [ ] Clicking a node opens right-side panel with node details and linked memories
- [ ] Panel shows: node type, properties, linked memories, source filename
- [ ] Filters: profile dropdown, node type checkboxes in side panel
- [ ] Mobile (< 768px): renders searchable concept list instead of Cytoscape
- [ ] Conflict nodes pulse amber via CSS animation
- [ ] "Open in Inbox" button on conflict nodes
- [ ] Graph loads within 2.5 seconds for up to 300 nodes
- [ ] Empty state: when no sources AND no processing jobs → First-Run Dashboard Experience

#### Checklist
- [ ] Cytoscape instance stored in `useRef` — NOT in React state
- [ ] `cytoscape-fcose` registered: `cytoscape.use(fcose)`
- [ ] `apiFetch` used for all data fetching — never raw `fetch()`
- [ ] Mobile detection via `useMediaQuery("(max-width: 768px)")`
- [ ] Node click calls `/v1/graph/neighborhood/{node_id}?hops=2`
- [ ] Conflict node CSS: `animate-pulse` on `bg-warning/20`
- [ ] Dynamic import of Cytoscape (not in initial bundle)
- [ ] Loading skeleton while graph fetches

#### Testing
```bash
# Manual test:
# 1. uv run python scripts/seed_dev_data.py
# 2. Open http://localhost:3000/graph
# 3. Verify force-directed graph renders
# 4. Click a concept node → verify right panel opens
# 5. Resize to 375px → verify list view renders
# 6. If conflict nodes exist → verify amber pulse animation
# 7. Click "Open in Inbox" on conflict node → verify navigation

# Build:
npm run build
# Expected: 0 TypeScript errors
```

---

### SUBCOMP-02D: Conflict Detection Worker

**Stories:** STORY-012
**Files:** `src/workers/conflict_tasks.py`, `src/services/conflict_service.py`, `tests/integration/workers/test_conflict_detection.py`

#### Details
The conflict detection worker (`scan_for_conflicts`) runs automatically after `write_graph_nodes` completes. It scans Qdrant for candidate contradictions using cosine similarity > 0.87, sends pairs to `LLMRouter().complete("conflict_classification")`, and creates Conflict records in PostgreSQL. Maximum 5 conflicts per ingestion batch to prevent notification fatigue.

#### Criteria of Done
- [ ] `scan_for_conflicts` task runs automatically after `write_graph_nodes`
- [ ] Qdrant cosine similarity scan: threshold 0.87, top-10 neighbors per memory
- [ ] All Qdrant queries include `tenant_id` filter — no cross-tenant data
- [ ] LLM classification: `LLMRouter().complete("conflict_classification")` with structured JSON output
- [ ] Classification categories: `CONTRADICTION`, `UPDATE`, `COMPLEMENT`, `DUPLICATE`
- [ ] Confidence < 0.70: pair skipped entirely
- [ ] CONFLICTING or UPDATE: `Conflict` record created in PostgreSQL with both memory snapshots
- [ ] CONTRADICTS Neo4j edge written between the two Memory nodes
- [ ] COMPLEMENT: `TEMPORAL_LINK` edge in Neo4j (no Conflict record)
- [ ] Auto-resolution: if authority weight delta >= 3 → `status=auto_resolved`
- [ ] Redis pub/sub notification: `conflict:new:{tenant_id}` after DB commit
- [ ] Maximum 5 conflicts per ingestion batch (capped)
- [ ] Same-source candidates skipped

#### Checklist
- [ ] Qdrant search uses `Filter(FieldCondition(key="tenant_id", ...))`
- [ ] Candidate list sliced to max 5 before creating Conflict records
- [ ] `maybe_auto_resolve()` checks authority weight delta >= 3
- [ ] `Conflict` record includes: both memory content snapshots, classification, confidence
- [ ] Redis notification fires AFTER PostgreSQL commit (not before)
- [ ] `scan_for_conflicts` enqueued from `write_graph_nodes` task on success
- [ ] Tenant isolation integration test mandatory before marking done

#### Testing
```bash
# Tenant isolation test:
uv run pytest tests/integration/workers/test_conflict_detection.py::test_conflict_detection_tenant_isolation -v

# Manual test — conflicting documents:
# 1. Upload doc1: "I am a senior Python developer"
# 2. Upload doc2: "I am a junior Python developer"
# 3. Check PostgreSQL conflicts table:
SELECT * FROM conflicts WHERE tenant_id = 'your-tenant';
# Expected: 1 conflict record with classification=CONTRADICTION

# Check Neo4j CONTRADICTS edge:
MATCH (m1:Memory)-[:CONTRADICTS]-(m2:Memory) RETURN m1, m2

# Quality:
make quality
```

---

### SUBCOMP-02E: Conflict Resolution API

**Stories:** STORY-013
**Files:** `src/api/routes/conflict.py`, `src/services/conflict_service.py`, `src/schemas/conflict.py`, `tests/integration/api/test_conflict_api.py`

#### Details
The Conflict Resolution API provides `GET /v1/conflicts` for listing pending conflicts, `POST /v1/conflicts/{id}/resolve` for three resolution actions, and `POST /v1/conflicts/{id}/undo` for reverting resolutions within a 30-second window. All mutations are atomic and tenant-scoped.

#### Criteria of Done
- [ ] `GET /v1/conflicts?status=pending` returns paginated list, newest first
- [ ] `POST /v1/conflicts/{id}/resolve` with `action=ACCEPT_NEW`: marks new `is_valid=true`, old `is_valid=false`, creates `SUPERSEDES` Neo4j edge
- [ ] `POST /v1/conflicts/{id}/resolve` with `action=KEEP_OLD`: marks resolved, no graph changes
- [ ] `POST /v1/conflicts/{id}/resolve` with `action=CUSTOM`: sends custom text to Claude Haiku, applies graph mutations
- [ ] `POST /v1/conflicts/{id}/undo` reverses resolution within 30-second window
- [ ] Undo after 30 seconds: returns `409 Conflict`
- [ ] Cross-user conflict resolution: returns `403`
- [ ] Response includes `graph_mutations` object showing what changed

#### Checklist
- [ ] `ConflictResponse`, `ResolveRequest`, `ResolveResponse` schemas in `src/schemas/conflict.py`
- [ ] `ResolveAction` enum: `ACCEPT_NEW`, `KEEP_OLD`, `CUSTOM`
- [ ] `GraphMutations` schema: `edges_added`, `nodes_updated`
- [ ] Undo window check: `resolved_at + 30s > now` — using `datetime.now(UTC)`
- [ ] SUPERSEDES edge in Neo4j wrapped in transaction (atomic)
- [ ] Always check `conflict.user_id == current_user["user_id"]` before mutation
- [ ] Use `PaginatedResponse` from `src/schemas/common.py`
- [ ] `redis.publish("conflict:resolved:{tenant_id}", ...)` after DB commit

#### Testing
```bash
# List pending conflicts:
curl "http://localhost:8000/v1/conflicts?status=pending" \
  -H "Authorization: Bearer TOKEN"
# Expected: paginated list of conflicts

# Resolve (accept new):
curl -X POST "http://localhost:8000/v1/conflicts/{id}/resolve" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "ACCEPT_NEW"}'
# Expected: 200 with graph_mutations

# Undo (within 30 seconds):
curl -X POST "http://localhost:8000/v1/conflicts/{id}/undo" \
  -H "Authorization: Bearer TOKEN"
# Expected: 200 if within window, 409 if expired

# Cross-user:
# Auth as different user → try to resolve user A's conflict
# Expected: 403

make quality
```

---

### SUBCOMP-02F: Memory Inbox UI

**Stories:** STORY-014
**Files:** `components/domain/MemoryInbox.tsx`, `components/domain/ConflictCard.tsx`, `components/domain/ConflictChat.tsx`, `hooks/use-keyboard-inbox.ts`, `app/(dashboard)/inbox/page.tsx`

#### Details
The Memory Inbox is the signature differentiator of Ravenbase. It surfaces contradictory facts for explicit human resolution through three flows: (1) Binary Triage with keyboard shortcuts J/K/Enter/Backspace, (2) Conversational Clarification with inline chat for nuanced resolutions, and (3) Optimistic Auto-Resolution with 30-second undo toast. All interactions use optimistic UI for sub-200ms perceived latency.

#### Criteria of Done
- [ ] Memory Inbox accessible at `/inbox`
- [ ] Flow 1 — Binary Triage: J/K cycles cards, Enter accepts AI resolution, Backspace keeps old
- [ ] Flow 2 — Conversational: C key expands card to inline chat; typing + Enter calls CUSTOM resolve
- [ ] Flow 3 — Auto-resolved: toast with 30-second countdown, Undo button
- [ ] Conflict count badge on sidebar nav icon (real-time via polling or SSE)
- [ ] Conflict card shows: incumbent text, challenger text, AI suggestion, source filenames, confidence badge
- [ ] Empty state after all conflicts resolved: "All clear! Your knowledge graph is up to date." with checkmark animation
- [ ] Optimistic UI: action completes in < 100ms perceived latency
- [ ] API failure after optimistic update: card re-appears with error toast
- [ ] `?` key shows keyboard shortcut reference tooltip
- [ ] Mobile (< 768px): full-width cards, 44px touch targets, swipe gestures as progressive enhancement

#### Checklist
- [ ] `use-keyboard-inbox.ts` hook handles J/K/Enter/Backspace/C/? on window level
- [ ] Keyboard handler ignores events when `HTMLInputElement` is focused (typing in chat)
- [ ] Optimistic update pattern: remove card immediately, revert on API error
- [ ] `useToast` with 30-second countdown timer for auto-resolved toast
- [ ] `ConflictCard` visual: `border-2 border-primary` for active, `opacity-70` for inactive
- [ ] OLD memory row: `bg-secondary/50 rounded-lg`; NEW memory row: `bg-primary/10 rounded-lg border border-primary/20`
- [ ] Confidence badge: `bg-warning text-[var(--warning-foreground)]`
- [ ] Mobile: `flex-1 h-11 sm:h-8` button sizing
- [ ] `swipe-right` Accept / `swipe-left` Keep Old as progressive enhancement
- [ ] Conflict count badge polls `GET /v1/conflicts?status=pending` or listens to SSE

#### Testing
```bash
# Manual test (requires seeded conflict data):
# 1. uv run python scripts/seed_dev_data.py (seed 3+ conflicts)
# 2. Open http://localhost:3000/inbox
# 3. Press J — move to next conflict
# 4. Press K — move to previous conflict
# 5. Press Enter — resolve with ACCEPT_NEW
# 6. Press Backspace — resolve with KEEP_OLD
# 7. Press C — expand chat mode, type custom text, press Enter
# 8. Resolve all — verify empty state renders
# 9. Disconnect network mid-resolve — verify rollback toast

# Build:
npm run build
# Expected: 0 TypeScript errors
```

---

### SUBCOMP-02G: Natural Language Graph Query — Backend

**Stories:** STORY-029
**Files:** `src/api/routes/graph.py`, `src/services/graph_query_service.py`, `src/schemas/graph.py`, `tests/integration/api/test_graph_query.py`

#### Details
The NL Graph Query backend (`POST /v1/graph/query`) accepts natural language questions, converts them to Cypher via `LLMRouter().complete("cypher_generation")` using Gemini 2.5 Flash, validates the generated Cypher is read-only, executes against Neo4j, and returns results in the same `GraphResponse` format as `GET /v1/graph/nodes`. This is Text-to-Cypher: the LLM generates Cypher, the service validates safety and injects tenant scoping, then executes.

#### Criteria of Done
- [ ] `POST /v1/graph/query` accepts `{query, profile_id?, limit?}` and returns `{cypher, results: {nodes, edges}, explanation, query_time_ms}`
- [ ] Cypher generated via `LLMRouter().complete("cypher_generation")` — Gemini 2.5 Flash primary, Claude Haiku fallback
- [ ] Safety validation: generated Cypher rejected if contains `CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DROP` — returns `422 UNSAFE_QUERY`
- [ ] `tenant_id` injected by `inject_tenant_filter()` — NEVER from LLM output
- [ ] Results returned in same `GraphResponse` shape: `{nodes: [...], edges: [...]}`
- [ ] `explanation` field: plain English description of what the query found
- [ ] `query_time_ms`: actual Neo4j execution time (not including LLM time)
- [ ] 2 credits deducted per query; `402` returned if insufficient credits
- [ ] `limit` defaults to 20, capped at 50 in code
- [ ] Empty results: returns `{nodes: [], edges: [], explanation: "No memories found..."}`

#### Checklist
- [ ] `GraphQueryRequest`, `GraphQueryResponse` schemas in `src/schemas/graph.py`
- [ ] `CYPHER_WRITE_KEYWORDS` regex: `r"\b(CREATE|MERGE|SET|DELETE|REMOVE|DROP|...)\b"`
- [ ] Safety check runs BEFORE execution — fail fast
- [ ] `inject_tenant_filter()` ensures every `MATCH` clause includes `tenant_id` scoping
- [ ] Anthropic import inside function body (`# noqa: PLC0415`)
- [ ] `max_tokens=512` on Cypher generation call
- [ ] Neo4j execution wrapped with timing measurement
- [ ] Credit check before LLM call (not after)
- [ ] `limit` capped at 50: `limit = min(limit, 50)`

#### Testing
```bash
# Happy path:
curl -X POST "http://localhost:8000/v1/graph/query" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show my Python projects from 2023", "limit": 10}'
# Expected: {"cypher": "MATCH (m:Memory)...", "results": {"nodes": [...], "edges": [...]},
#            "explanation": "Found 5 memory nodes matching your query.", "query_time_ms": 42}

# Safety test (must return 422):
curl -X POST "http://localhost:8000/v1/graph/query" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Delete all my memories"}'
# Expected: 422 {"detail": {"code": "UNSAFE_QUERY", "message": "Query must be read-only"}}

# Zero results:
curl -X POST "http://localhost:8000/v1/graph/query" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "xyzzy nothing matches this"}'
# Expected: {"nodes": [], "edges": [], "explanation": "No memories found matching your query."}

make quality
```

---

### SUBCOMP-02H: Natural Language Graph Query — Frontend

**Stories:** STORY-030
**Files:** `components/domain/GraphExplorer.tsx`, `components/domain/GraphQueryBar.tsx`, `components/domain/GraphQueryResults.tsx`

#### Details
The NL Graph Query frontend extends the Graph Explorer with a query bar above the filter controls. Users type natural language questions, submit, and see matching nodes highlighted in amber on the Cytoscape graph with a results panel showing memory cards. A "Show Cypher" toggle reveals the generated query for power users.

#### Criteria of Done
- [ ] Query bar renders above filter bar: `[Ask your graph anything...] [Search]`
- [ ] User submits query → matching nodes highlighted amber (`#ffc00d`) in Cytoscape
- [ ] Results panel slides in from right showing matched Memory nodes as cards
- [ ] Result card shows: content preview (first 150 chars), source filename, confidence badge
- [ ] Clicking a result card centers Cytoscape on that node and opens node detail panel
- [ ] Expandable "Show Cypher" section shows generated Cypher query
- [ ] Example query chips when input empty: "Show my Python projects", "Skills since 2023", "What did I decide about databases?"
- [ ] Clearing query restores all nodes to default colors (unhighlights)
- [ ] Zero results: "No memories found. Try a different question." with empty state illustration
- [ ] Mobile (< 768px): query bar above concept list, example chips `flex-wrap`

#### Checklist
- [ ] `GraphQueryBar` component: controlled `Input` + `Button`, `onKeyDown` for Enter
- [ ] `useApiFetch()` hook for `POST /v1/graph/query` (client component)
- [ ] Node highlighting: `cy.elements().removeClass("query-match")` + `cy.getElementById(id).addClass("query-match")`
- [ ] Amber highlighted style: `{"background-color": "#ffc00d", "border-width": 3}` in Cytoscape stylesheet
- [ ] `cy.fit(cy.elements(".query-match"), 80)` to center matched nodes
- [ ] Example chips: clicking sets input value, does NOT submit
- [ ] Zero-state message component when `results.nodes.length === 0`
- [ ] "Show Cypher" expandable below results with `font-mono text-sm` styling
- [ ] Mobile: `flex-wrap gap-2` on example chips

#### Testing
```bash
# Manual test:
# 1. Navigate to /graph
# 2. Verify query bar appears above filter row
# 3. Click an example chip — verify it fills the query input
# 4. Submit query "Show my Python projects"
# 5. Verify: matching nodes turn amber in graph
# 6. Verify: results panel slides in from right with memory cards
# 7. Click a result card — verify graph centers on that node
# 8. Click "Show Cypher" — verify Cypher is displayed
# 9. Click Clear — verify all nodes return to default colors
# 10. Test with query returning nothing — verify empty state message

# Build:
npm run build
# Expected: 0 TypeScript errors
```
