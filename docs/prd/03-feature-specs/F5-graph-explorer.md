# Feature Spec — F5: Graph Explorer

> **Stories:** STORY-011
> **Cross-references:** `architecture/02-database-schema.md` (Neo4j schema) | `design/03-screen-flows.md`

## Overview
A visual interface for exploring the user's Knowledge Graph. Force-directed graph on desktop using Cytoscape.js; degrades gracefully to searchable list on mobile.

## Node Visualization

| Node Type | Color | Shape | Size |
|---|---|---|---|
| `concept` | `blue-500` | Circle | Based on memory_count (min 20px, max 50px) |
| `memory` | `slate-400` | Round-rectangle | Fixed 16px |
| `source` | `violet-500` | Diamond | Fixed 24px |
| `metadoc` | `amber-500` | Star | Fixed 28px |
| `conflict (pending)` | `amber-500` pulsing | Circle | Fixed 32px |
| `conflict (resolved)` | `emerald-500` | Circle | Fixed 20px |

## Interactions

| Interaction | Behavior |
|---|---|
| Click node | Open `<GraphNodePanel />` as right Sheet |
| Click conflict node | Show "Open in Inbox" shortcut |
| Double-click | Zoom to node + show neighborhood |
| Hover | Highlight connected edges, show node label |
| Click edge | Show relationship type tooltip |
| Filter change | Re-render with filtered nodes (no page reload) |

## Acceptance Criteria
- [ ] Graph renders up to 300 nodes without performance issues (60fps)
- [ ] Node colors + shapes match the specification above
- [ ] Conflict nodes pulse amber (CSS animation, not JS)
- [ ] Click → side panel open with node details + linked memories + sources
- [ ] Filters (profile, date range, node type) work without page reload
- [ ] Mobile: renders `<ConceptList />` searchable list instead of graph
- [ ] Empty state: illustrated message + "Upload your first file" CTA
- [ ] "Open in Inbox" button on conflict nodes works
