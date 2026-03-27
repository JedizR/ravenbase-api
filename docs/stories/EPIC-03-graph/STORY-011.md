# STORY-011: Graph Explorer UI (Cytoscape.js)

**Epic:** EPIC-03 — Knowledge Graph Layer
**Priority:** P1
**Complexity:** Large
**Depends on:** STORY-010

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-04-AC-1: GET /v1/graph/nodes returns all Concept and Memory nodes for the authenticated tenant
- FR-04-AC-2: Empty graph returns {nodes:[], edges:[]} — never 404
- FR-04-AC-3: GET /v1/graph/neighborhood/{node_id} returns N-hop subgraph (default hops=2, max hops=5)
- FR-04-AC-4: tenant_id comes from JWT only — never from query params
- FR-04-AC-5: Optional profile_id filter scopes results to a profile

## Component
COMP-02: GraphEngine

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (apiFetch, no form tags, Tailwind only)
> 3. `docs/design/01-design-system.md` — node colors, dark mode tokens
> 4. `docs/design/03-screen-flows.md` — Graph Explorer layout spec
> 5. `docs/architecture/03-api-contract.md` — `/v1/graph/nodes` and `/v1/graph/neighborhood/{node_id}` response shapes

---

## User Story
As a user, I want to visually explore my knowledge graph so that I can see how my concepts and memories connect over time.

## Context
- Design system: `design/01-design-system.md` — node colors, dark mode
- Screen flows: `design/03-screen-flows.md` — Graph Explorer layout
- API: STORY-010 endpoints (`/v1/graph/nodes`, `/v1/graph/neighborhood/{node_id}`)

## Acceptance Criteria
- [ ] AC-1: Graph Explorer renders force-directed graph using Cytoscape.js
- [ ] AC-2: Node types have distinct colors: concept=blue, memory=slate, source=violet, conflict=amber (pulsing)
- [ ] AC-3: Clicking a node opens a right side panel with node details and linked memories
- [ ] AC-4: Filters work: profile, date range, node type (checkboxes in side panel)
- [ ] AC-5: On mobile (< 768px): gracefully degrades to searchable list of concepts (not force graph)
- [ ] AC-6: Conflict nodes pulse amber to draw attention (CSS animation)
- [ ] AC-7: "Open in Inbox" button on conflict nodes jumps to Memory Inbox filtered to that conflict
- [ ] AC-8: Graph loads within 2.5 seconds for up to 300 nodes
- [ ] AC-9: Empty state: when `sources.length === 0` AND no jobs are processing, renders the State 2 empty state from `docs/design/04-ux-patterns.md` → "First-Run Dashboard Experience". When a processing job is active (`job.status === "PROCESSING"`), renders the State 1 "Building Graph" animation instead. Never shows a blank void.

## Technical Notes

### Files to Create (Frontend)
- `components/domain/GraphExplorer.tsx` — main Cytoscape.js wrapper
- `components/domain/GraphNodePanel.tsx` — right side panel
- `components/domain/GraphFilters.tsx` — filter controls
- `app/(dashboard)/graph/page.tsx` — page layout

### Additional Packages Required
```bash
npm install cytoscape @types/cytoscape cytoscape-fcose
```
- `cytoscape` — graph visualization core
- `cytoscape-fcose` — force-directed layout (better performance than default cose)

### Architecture Constraints
- Use `apiFetch` from `@/lib/api` for all data fetching — never raw `fetch()`
- Cytoscape instance created via `useRef` — do NOT store in React state
- Node click calls `/v1/graph/neighborhood/{node_id}` to load subgraph
- Mobile detection: `useMediaQuery("(max-width: 768px)")` — render list if true
- No `<form>` tags in filter panel — use controlled inputs + onClick

### Cytoscape Setup Pattern
```typescript
// components/domain/GraphExplorer.tsx
"use client";
import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import { apiFetch } from "@/lib/api";

cytoscape.use(fcose);

const NODE_COLORS: Record<string, string> = {
  concept: "#2d4a3e",   // primary green (from design system)
  memory: "#e8ebe6",    // secondary (forest secondary)
  source: "#a8c4b2",    // accent (sage green)
  conflict: "#ffc00d",  // warning amber (from design system)
};

export function GraphExplorer({ profileId }: { profileId: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    apiFetch<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
      `/v1/graph/nodes?profile_id=${profileId}&limit=200`
    ).then(({ nodes, edges }) => {
      cyRef.current = cytoscape({
        container: containerRef.current,
        elements: [
          ...nodes.map((n) => ({
            data: { id: n.id, label: n.label, type: n.type },
          })),
          ...edges.map((e) => ({
            data: { source: e.source, target: e.target, type: e.type },
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              "background-color": (ele) =>
                NODE_COLORS[ele.data("type")] ?? "#d1d5db",  // border color as fallback
              label: "data(label)",
              color: "#ffffff",  // primary-foreground
              "font-size": 10,
            },
          },
        ],
        layout: { name: "fcose" },
      });

      cyRef.current.on("tap", "node", (evt) => {
        const node = evt.target;
        // Open GraphNodePanel for clicked node
      });
    });

    return () => cyRef.current?.destroy();
  }, [profileId]);

  return <div ref={containerRef} className="w-full h-full" />;
}
```

### Conflict Node Pulse Animation
```css
/* globals.css */
/* Use Tailwind animate-pulse on bg-warning/20 outer wrapper — no custom keyframe needed */
/* Conflict node in Cytoscape uses bg-warning (#ffc00d) fill */
/* For the Cytoscape node itself, apply a CSS class with animation: */
.conflict-node {
  animation: pulse 2s ease-in-out infinite;  /* uses Tailwind's built-in pulse */
}
```

## Definition of Done
- [ ] Graph renders with 100+ seeded nodes without performance issues
- [ ] All ACs verified manually
- [ ] Mobile degrades to list view at 375px
- [ ] Conflict nodes pulse amber
- [ ] No TypeScript errors (`npm run build` passes)

## Testing This Story

```bash
# Frontend build check:
npm run build

# Manual test:
# 1. Seed data: uv run python scripts/seed_dev_data.py
# 2. Open http://localhost:3000/dashboard/graph
# 3. Verify graph renders with nodes and edges
# 4. Click a concept node — verify right panel opens
# 5. Resize to 375px — verify list view renders
# 6. If conflict nodes exist — verify amber pulse animation
```

**Passing result:** Graph renders force-directed layout. Clicking nodes opens detail panel. Mobile shows searchable list. Conflict nodes pulse amber.

---

## Agent Implementation Brief

```
Implement STORY-011: Graph Explorer UI (Cytoscape.js).

Read first:
1. CLAUDE.md (architecture rules)
2. docs/design/CLAUDE_FRONTEND.md (apiFetch, no form tags, Tailwind only)
3. docs/design/01-design-system.md (color tokens for node types)
4. docs/design/03-screen-flows.md (Graph Explorer layout spec)
5. docs/architecture/03-api-contract.md (/v1/graph/nodes response shape)
6. docs/stories/EPIC-03-graph/STORY-011.md (this file)

Key constraints:
- Install: npm install cytoscape @types/cytoscape cytoscape-fcose
- Cytoscape instance in useRef — NOT React state (avoid re-render performance issues)
- All data via apiFetch — never raw fetch()
- Mobile breakpoint (< 768px): render ConceptList instead of Cytoscape graph
- Conflict nodes need CSS pulse animation (bg-warning #ffc00d, using animate-pulse)
- Node click triggers apiFetch to /v1/graph/neighborhood/{node_id}?hops=2

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# 1. Quality gate:
make quality && make test       # backend
npm run build && npm run test   # frontend (if applicable)

# 2. Commit:
git add -A && git commit -m "feat(ravenbase): STORY-011 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-011"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-011
git add docs/stories/epics.md && git commit -m "docs: mark STORY-011 complete"
```
