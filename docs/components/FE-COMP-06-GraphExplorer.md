# GraphExplorer

> **Component ID:** FE-COMP-06
> **Epic:** EPIC-03 — Knowledge Graph Layer
> **Stories:** STORY-011, STORY-030
> **Type:** Frontend (Dashboard)

---

## Purpose

The Graph Explorer is the visual interface for Ravenbase's hybrid vector + knowledge graph. It renders a force-directed graph of Concept, Memory, Source, and Conflict nodes using Cytoscape.js with the `fcose` layout algorithm. Users click nodes for details, filter by profile/date/type, and run natural language graph queries. On mobile (< 768px) it degrades to a searchable concept list. MUST use `dynamic(() => import(...), { ssr: false })` — Cytoscape is a browser-only library.

---

## ⚠️ Dynamic Import Required

```tsx
// app/(dashboard)/graph/page.tsx — SSR will crash without this
import dynamic from "next/dynamic"

const GraphExplorer = dynamic(
  () => import("@/components/domain/GraphExplorer"),
  { ssr: false, loading: () => <Skeleton className="w-full h-150 rounded-2xl" /> }
)
```

Actual URL: `/graph` (NOT `/dashboard/graph`)

---

## User Journey

1. User navigates to `/graph`
2. Skeleton loading state while `GET /v1/graph/nodes` fetches

**If empty (0 nodes):**
- Empty state: illustrated graph icon + "Upload your first file to build your graph"
- CTA links to `/sources`

**If has nodes:**
3. Cytoscape.js renders force-directed layout (`fcose` algorithm)
4. Nodes colored by type: Concept=primary green, Memory=secondary sage, Source=accent, Conflict=amber warning pulsing
5. Conflict nodes: pulsing amber ring (`animate-pulse` + `bg-warning/20`)

**Node interaction:**
6. Click node → `GraphNodePanel` slides in from right
   - Shows: label, type, connected nodes, source reference
   - For conflict nodes: "Open in Memory Inbox" button → `/inbox?focus_id=...`
7. Type NL query in `GraphQueryBar` → `POST /v1/graph/query`
   - Returns: highlighted subgraph + explanation
   - Cost: 2 credits (0 for admin users — backend handles bypass)

**Controls:**
- Zoom: `+`/`-` buttons, scroll, pinch
- Fit: `F` key or "Fit" button
- Filters: profile dropdown, date range picker, node type checkboxes

**Mobile (< 768px):**
- Cytoscape NOT rendered (performance)
- Replaced with searchable concept list (`<ConceptList>`)
- `useMediaQuery("(max-width: 768px)")` detects breakpoint

---

## Subcomponents

```
components/domain/
  GraphExplorer.tsx      — Main Cytoscape.js wrapper (browser-only, dynamic import)
  GraphNodePanel.tsx     — Right-side node detail panel (slide-in)
  GraphFilters.tsx       — Filter controls: profile, date range, node type checkboxes
  GraphControls.tsx      — Zoom + fit controls overlay (absolute positioned)
  GraphQueryBar.tsx      — NL query input (BUG-025: example clicks fill but don't auto-execute)
  ConceptList.tsx        — Mobile fallback: searchable concept list

hooks/
  use-graph-data.ts      — TanStack Query wrapper for graph endpoints
  use-media-query.ts     — Mobile breakpoint detection

app/(dashboard)/graph/
  page.tsx               — Page with dynamic GraphExplorer import
  GraphPageClient.tsx    — Client-side state: filters, selected node, NL query
  loading.tsx            — Skeleton loading state
```

---

## API Contracts

```
GET /v1/graph/nodes?profile_id=&limit=300
  Response: { nodes: [{id, label, type, properties}], edges: [{source, target, type}] }
  Auth:     Required
  staleTime: 60_000

GET /v1/graph/neighborhood/{node_id}?depth=2
  Response: { nodes, edges } — subgraph around this node
  Auth:     Required
  Used by:  GraphNodePanel

POST /v1/graph/query
  Request:  { query: string, profile_id?: string, limit?: number }
  Response: { cypher: string, results: {nodes, edges}, explanation: string, credits_consumed: number }
  Auth:     Required
  Cost:     2 credits per call (0 for admin — backend CreditService bypass)
```

---

## Admin Bypass

NL graph queries cost 2 credits per query. Admin users: backend `CreditService.check_or_raise()` skips → queries run for free. No frontend changes needed — credit display in sidebar shows `◆ ADMIN_ACCESS` instead of credit count.

---

## Design System Rules

Cross-reference: `docs/design/AGENT_DESIGN_PREAMBLE.md` (READ FIRST)

Specific rules:
- **Node colors (Cytoscape style):** Concept=`var(--primary)` (#2d4a3e), Memory=`var(--secondary)` (#e8ebe6), Source=`var(--accent)` (#a8c4b2), Conflict=`var(--warning)` (#ffc00d)
- **Conflict node:** `border-width: 3`, `border-color: var(--warning)`, `animate-pulse` ring
- **Node panel:** `w-80 border-l border-border bg-card` — slides in from right
- **Filter sidebar:** `bg-card border-r border-border` or integrated as overlay
- **Controls:** `absolute top-4 right-4` overlay on graph area
- **Cytoscape instance:** MUST be stored in `useRef` — NEVER `useState` (causes infinite re-render)
- **Layout call order:** `cytoscape.use(fcose)` BEFORE creating any Cytoscape instance

---

## Known Bugs / Current State

**BUG-018 (HIGH):** Date range filter UI exists but is NEVER applied to filtered nodes.
- **Root cause:** `app/(dashboard)/graph/GraphPageClient.tsx:38-70` — `dateRange.from` and `dateRange.to` are collected in state but `filteredNodes` calculation at line 51 ignores them entirely. The filter only applies `nodeTypeFilter` and `profileId` — date range has no effect.
- **Fix:** In `filteredNodes` useMemo, add date filtering:
  ```typescript
  .filter(node => {
    if (!dateRange.from && !dateRange.to) return true
    const nodeDate = new Date(node.properties?.created_at ?? 0)
    if (dateRange.from && nodeDate < dateRange.from) return false
    if (dateRange.to && nodeDate > dateRange.to) return false
    return true
  })
  ```
- **Story:** STORY-039

**BUG-025 (LOW):** GraphQueryBar example query clicks only fill the input — don't auto-execute.
- **Root cause:** `components/domain/GraphQueryBar.tsx:91` — `onClick` sets the input value but doesn't call `handleSubmit()`. User has to press Enter again.
- **Fix:** Call `handleSubmit(exampleQuery)` directly on example click.
- **Story:** STORY-041

**Existing code pattern verification needed:**
- Verify Cytoscape instance stored in `useRef` (NOT `useState`) — infinite re-render risk
- Verify `cytoscape.use(fcose)` called before creating Cytoscape instance

---

## Acceptance Criteria

- [ ] `/graph` renders Cytoscape graph (or empty state) without SSR crash
- [ ] `dynamic(() => import(...), { ssr: false })` used for GraphExplorer component
- [ ] Nodes colored by type: Concept=green, Memory=sage, Source=sage, Conflict=amber
- [ ] Conflict nodes have pulsing amber ring
- [ ] Click node → GraphNodePanel slides in from right with node details
- [ ] "Open in Inbox" button on conflict nodes → navigates to `/inbox?focus_id=...`
- [ ] Profile filter → graph refetches with `profile_id` param
- [ ] Date range filter → `filteredNodes` actually filters by date (BUG-018 fixed)
- [ ] NL query → `POST /v1/graph/query` fires → subgraph highlighted + explanation shown
- [ ] Mobile (375px) → Cytoscape NOT rendered → `<ConceptList>` shown instead
- [ ] Empty state (no sources) → upload CTA to `/sources`
- [ ] Cytoscape instance in `useRef` not `useState`
- [ ] `cytoscape.use(fcose)` called exactly once before instance creation

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `BE-COMP-02-GraphEngine.md` — graph API endpoints, NL query generation
- `BE-COMP-06-CreditSystem.md` — 2 credit cost for NL queries (admin bypass)
- `docs/architecture/03-api-contract.md` — graph endpoints
- `docs/components/REFACTOR_PLAN.md` — BUG-018, BUG-025 fix details

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-011](docs/stories/EPIC-03-graph/STORY-011.md) | Graph Explorer UI | Frontend | Full graph visualization with Cytoscape |
| [STORY-010](docs/stories/EPIC-03-graph/STORY-010.md) | Graph API Endpoints | Backend | /v1/graph/nodes and /v1/graph/neighborhood |
| [STORY-030](docs/stories/EPIC-09-memory-intelligence/STORY-030.md) | NL Graph Query Frontend | Frontend | Natural language query input |

---

## Cytoscape Setup Pattern

```tsx
// components/domain/GraphExplorer.tsx — MUST be dynamic imported
"use client"
import { useEffect, useRef } from "react"
import cytoscape from "cytoscape"
import fcose from "cytoscape-fcose"

// Call ONCE at module level — before any instance creation
cytoscape.use(fcose)

const NODE_COLORS: Record<string, string> = {
  concept:  "var(--primary)",    // #2d4a3e forest green
  memory:   "var(--secondary)",  // #e8ebe6 sage
  source:   "var(--accent)",     // #a8c4b2 light sage
  conflict: "var(--warning)",    // #ffc00d amber
}

export function GraphExplorer({ profileId }: { profileId: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)  // MUST be useRef, never useState

  useEffect(() => {
    if (!containerRef.current) return
    // fetch + init cytoscape...
    return () => cyRef.current?.destroy()
  }, [profileId])

  return <div ref={containerRef} className="w-full h-full" />
}
```

## Date Range Filter Fix (BUG-018)

```typescript
// app/(dashboard)/graph/GraphPageClient.tsx — FIXED filteredNodes
const filteredNodes = useMemo(() => {
  return nodes
    .filter(n => nodeTypeFilter.includes(n.type))
    .filter(n => {
      // BUG-018 FIX: was never applied
      if (!dateRange.from && !dateRange.to) return true
      const nodeDate = new Date(n.properties?.created_at ?? 0)
      if (dateRange.from && nodeDate < dateRange.from) return false
      if (dateRange.to && nodeDate > dateRange.to) return false
      return true
    })
}, [nodes, nodeTypeFilter, dateRange])
```
