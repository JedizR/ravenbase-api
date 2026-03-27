# STORY-030: Natural Language Graph Query — Frontend

**Epic:** EPIC-09 — Memory Intelligence
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-029 (backend query endpoint), STORY-011 (Graph Explorer must exist)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-13-AC-1: POST /v1/graph/query accepts natural language input
- FR-13-AC-2: LLMRouter generates safe read-only Cypher
- FR-13-AC-3: Generated Cypher validated — write operations rejected
- FR-13-AC-4: Query results returned as GraphResponse

## Component
COMP-02: GraphEngine

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` (frontend CLAUDE.md in repo root) — frontend rules
> 2. `docs/design/CLAUDE_FRONTEND.md` — useApiFetch, no form tags, approved packages
> 3. `docs/design/01-design-system.md` — dark mode tokens, muted colors for secondary UI
> 4. `docs/stories/EPIC-03-graph/STORY-011.md` — Graph Explorer component structure to extend

---

## User Story
As a user, I want to type a question about my knowledge graph and see the matching
nodes highlighted, so that I can explore my memories without knowing Cypher syntax.

## Context
- Extends STORY-011's Graph Explorer with a query bar above the graph
- Uses STORY-029's `POST /v1/graph/query` endpoint
- Results: highlight matching nodes in the Cytoscape graph AND show result cards in a panel
- Transparency: "Show Cypher" expandable shows generated Cypher for power users
- Example queries reduce friction for new users

## Acceptance Criteria
- [ ] AC-1: Graph Explorer shows a query bar above the filter bar: `[Ask your graph anything...] [Search]`
- [ ] AC-2: User submits query → loading spinner → matching nodes highlighted amber in graph
- [ ] AC-3: Results panel slides in from the right showing matched Memory nodes as cards
- [ ] AC-4: Each result card shows: content preview (first 150 chars), source filename, confidence badge
- [ ] AC-5: Clicking a result card centers the graph on that node and opens the node detail panel
- [ ] AC-6: Expandable "Show Cypher" section below results shows the generated Cypher query
- [ ] AC-7: Example query chips displayed when query bar is empty: "Show my Python projects", "Skills since 2023", "What did I decide about databases?"
- [ ] AC-8: Clearing the query bar restores all graph nodes to their default colors (unhighlights)
- [ ] AC-9: Zero results: shows "No memories found. Try a different question." with empty state illustration
- [ ] AC-10: Mobile (< 768px): query bar appears above the concept list (not the graph);
  example chips use `flex-wrap gap-2` and wrap without overflow at 375px

## Technical Notes

### Files to Create/Modify
- `components/domain/GraphExplorer.tsx` — add `GraphQueryBar` + result highlighting logic
- `components/domain/GraphQueryBar.tsx` — new component: query input + submit + example chips
- `components/domain/GraphQueryResults.tsx` — results panel with memory cards + Cypher reveal

### Mobile

On mobile the Cytoscape graph degrades to the concept list (from STORY-011). The query
bar sits above the list. Results appear as list items below. The example chips use
`flex-wrap gap-2` which handles wrapping at 375px without overflow.

### Architecture Constraints
- `"use client"` — all graph explorer components are already client-side
- Use `useApiFetch()` hook for the `POST /v1/graph/query` call
- Node highlighting: Cytoscape's `cy.elements().removeClass("highlighted")` + add class to matched nodes
- Cytoscape style for highlighted nodes: `{ "background-color": "#ffc00d", "border-width": 3 }` (warning amber from design system)
- Do not create a separate page — this is an enhancement to the existing Graph Explorer

### GraphQueryBar Component

```tsx
// components/domain/GraphQueryBar.tsx
"use client";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Search } from "lucide-react";

const EXAMPLE_QUERIES = [
  "Show my Python projects",
  "Skills I've learned since 2023",
  "What decisions did I make about databases?",
  "Find memories about machine learning",
];

interface GraphQueryBarProps {
  onResults: (results: GraphQueryResponse | null) => void;
  profileId: string | undefined;
}

export function GraphQueryBar({ onResults, profileId }: GraphQueryBarProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const apiFetch = useApiFetch();

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await apiFetch<GraphQueryResponse>("/v1/graph/query", {
        method: "POST",
        body: JSON.stringify({ query, profile_id: profileId, limit: 20 }),
      });
      onResults(data);
    } catch (err) {
      toast.error("Query failed. Try rephrasing.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setQuery("");
    onResults(null);  // clears highlights
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <Input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") handleSearch(); }}
          placeholder="Ask your graph anything..."
          className="font-mono text-sm"
        />
        {query && (
          <Button variant="ghost" size="sm" onClick={handleClear}>Clear</Button>
        )}
        <Button onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        </Button>
      </div>

      {!query && (
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map(eq => (
            <button
              key={eq}
              onClick={() => setQuery(eq)}
              className="text-xs font-mono text-muted-foreground border border-border
                         rounded px-2 py-0.5 hover:border-primary hover:text-primary transition-colors"
            >
              {eq}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Node Highlighting Integration

```tsx
// In GraphExplorer.tsx — add to the cyRef.current setup and when queryResults change

useEffect(() => {
  if (!cyRef.current) return;
  const cy = cyRef.current;

  if (!queryResults) {
    cy.elements().removeClass("query-match");
    return;
  }

  cy.elements().removeClass("query-match");
  const matchedIds = queryResults.results.nodes.map(n => n.id);
  matchedIds.forEach(id => {
    cy.getElementById(id).addClass("query-match");
    cy.getElementById(id).select();
  });

  if (matchedIds.length > 0) {
    cy.fit(cy.elements(".query-match"), 80);
  }
}, [queryResults]);

// Cytoscape stylesheet addition (add to existing styles array):
{
  selector: ".query-match",
  style: {
    "background-color": "#ffc00d",  // warning amber from design system
    "border-width": 3,
    "border-color": "#d97706",  // slightly darker amber for border contrast
    "z-index": 999,
  },
},
```

## Definition of Done
- [ ] Query bar renders above the filter bar in Graph Explorer
- [ ] Submitting a query highlights matching nodes amber in Cytoscape
- [ ] Results panel shows memory cards (preview + source + confidence)
- [ ] Clicking a result card centers graph + opens node detail panel
- [ ] "Show Cypher" expandable reveals generated Cypher
- [ ] Example query chips appear when input is empty; clicking fills the input
- [ ] Clearing query restores default node colors
- [ ] Zero results shows empty state message
- [ ] `npm run build` passes (0 TypeScript errors)

## Testing This Story

```bash
# Build check:
npm run build

# Manual test:
# 1. Navigate to /dashboard/graph
# 2. Verify query bar appears above filter row
# 3. Click an example chip — verify it fills the query input
# 4. Submit query "Show my Python projects"
# 5. Verify: matching nodes turn amber in graph
# 6. Verify: results panel slides in from right with memory cards
# 7. Click a result card — verify graph centers on that node
# 8. Click "Show Cypher" — verify Cypher is displayed
# 9. Click Clear — verify all nodes return to default colors
# 10. Test with a query that returns nothing — verify empty state message
```

---

## Agent Implementation Brief

```
Implement STORY-030: Natural Language Graph Query — Frontend.
Backend is complete. Run npm run generate-client first.

Read first:
1. CLAUDE.md (frontend rules in this repo root)
2. docs/design/CLAUDE_FRONTEND.md (useApiFetch hook, no form tags)
3. docs/stories/EPIC-03-graph/STORY-011.md (existing Cytoscape setup to extend)
4. docs/stories/EPIC-09-memory-intelligence/STORY-030.md (this file)

Key constraints:
- "use client" already on GraphExplorer — add query bar as a child component
- useApiFetch() hook for POST /v1/graph/query (client component)
- Cytoscape highlighting: cy.elements().removeClass() + cy.getElementById(id).addClass()
- Example chips: clicking sets the input value, does NOT submit immediately
- No <form> tags — Input with onKeyDown for Enter + Button with onClick

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
npm run build && npm run test
git add -A && git commit -m "feat(ravenbase): STORY-030 natural language graph query frontend"
git push
# Edit docs/stories/epics.md → ✅ for STORY-030
git add docs/stories/epics.md && git commit -m "docs: mark STORY-030 complete"
```
