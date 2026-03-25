# Feature Spec — F3: Memory Inbox

> **Cross-references:** `stories/EPIC-04-conflict/STORY-012-014.md` | `design/04-ux-patterns.md`

---

## Overview

The Memory Inbox is the **signature differentiator** of Ravenbase. When the Conflict Detection Agent identifies contradictory facts in the user's knowledge graph, it surfaces them here for explicit human resolution.

**Philosophy:** Memory is never overwritten without consent. Contradictions become trust-building interactions, not silent data loss.

---

## Conflict Detection Algorithm (5 Steps)

```
Step 1 — Embedding Similarity Scan
  After each ingestion batch completes:
  Qdrant: find all new Memory node embeddings
  For each new embedding: search top-10 nearest neighbors (cosine > 0.87)
  Filter: same tenant_id, different source_id, is_valid=true

Step 2 — LLM Classification
  Candidate pairs → Claude Haiku (JSON mode)
  → {classification: CONTRADICTION|UPDATE|COMPLEMENT|DUPLICATE, confidence, reasoning}
  Skip pairs with confidence < 0.70

Step 3 — Temporal Weighting
  CONTRADICTION or UPDATE:
  → Determine incumbent (older created_at) and challenger (newer)
  → Tag challenger as "proposed update"

Step 4 — Authority Weighting (Auto-Resolution)
  Check SourceAuthorityWeight for both source types
  If challenger authority > incumbent by ≥ 3 points:
  → Auto-resolve: set incumbent is_valid=false, challenger is_valid=true
  → status = "auto_resolved"
  → Publish undo-capable toast notification

Step 5 — Inbox Delivery
  Remaining unresolved conflicts:
  → Create Conflict record in PostgreSQL
  → Write CONTRADICTS edge in Neo4j
  → Publish to Redis: conflict:new:{tenant_id}
  → Sort by: confidence desc, created_at desc
  → Cap at 5 conflicts per ingestion batch (notification fatigue prevention)
```

---

## Three UX Resolution Flows

### Flow 1: Binary Triage (Default — Keyboard-First)

**Target:** Simple contradictions where AI's proposed resolution is clear.
**UX:** Central card; no mouse required.

```
User sees:
┌───────────────────────────────────────────────────────┐
│  ◆ MEMORY_CONFLICT          [confidence: 94%]         │
│                                                       │
│  OLD  "I use React for all frontend development"      │
│  NEW  "I now exclusively use Vue.js at work"          │
│                                                       │
│  AI suggests: Update primary stack to Vue.js.         │
│              Tag React as "Past Skill (2021-2023)"    │
│                                                       │
│  [Enter → Accept]  [Backspace → Keep Old]  [C → Chat] │
│  Source: chat_export_2022.json → notes_march_2024.md  │
└───────────────────────────────────────────────────────┘

Keyboard shortcuts:
  J / K      → next / previous conflict card
  Enter      → ACCEPT_NEW (accept AI resolution)
  Backspace  → KEEP_OLD (dismiss challenger)
  C          → enter conversational mode (Flow 2)
  ?          → show keyboard shortcut reference
```

**UI update:** Optimistic — card animates out immediately. API call happens in background. If API fails: card animates back in with error toast.

---

### Flow 2: Conversational Clarification (Inline Chat)

**Target:** Ambiguous conflicts requiring nuanced user input.
**Trigger:** Press `C` on any conflict card.

```
Card expands to show:
┌─────────────────────────────────────────────────────┐
│  OLD  "I use React for frontend"                    │
│  NEW  "I use Vue.js exclusively"                    │
│                                                     │
│  [Source: chat_2022.json] [Source: notes_2024.md]   │
│                                                     │
│  AI: Both sources seem credible. Can you clarify?   │
│  "Do you still use React (e.g. for side projects),  │
│   or have you fully switched to Vue?"               │
│                                                     │
│  > [user types here...]                             │
│                                                     │
│  [Enter to resolve]  [Esc to cancel]                │
└─────────────────────────────────────────────────────┘

User types: "I use Vue at work but React for personal projects"
→ Claude Haiku generates graph mutations:
  - Tag Memory A: "skill:react:context=personal_projects"
  - Tag Memory B: "skill:vue:context=work:is_primary=true"
→ Updates applied to Neo4j
→ Brief visualization flash: graph edges update
```

---

### Flow 3: Optimistic Auto-Resolution with Undo

**Target:** Low-stakes conflicts where source authority makes the answer obvious.
**Trigger:** Auto-resolution from conflict_worker.

```
User sees (toast notification, bottom-right):
┌────────────────────────────────────┐
│ Updated primary framework to Vue.  │
│ React tagged as Past Skill.  [Undo]│
│ ▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░  28s          │
└────────────────────────────────────┘

Undo window: 30 seconds
→ Click Undo: calls POST /v1/conflicts/{id}/undo
→ Toast replaces: "Reverted. Conflict added to your Inbox."
```

---

## User Stories

| ID | Story | Priority |
|---|---|---|
| US-F3-01 | As a user, I want a notification badge on the Inbox icon showing pending conflict count | P0 |
| US-F3-02 | As a user, I want to accept/reject a conflict with a single keystroke | P0 |
| US-F3-03 | As a user, I want to expand a conflict into conversational mode for nuanced resolution | P0 |
| US-F3-04 | As a user, I want auto-resolution for low-stakes conflicts with Undo capability | P1 |
| US-F3-05 | As a user, I want to see the graph update live when I resolve a conflict | P1 |
| US-F3-06 | As a user, I want an accessible keyboard shortcut reference (?) | P2 |

---

## Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-F3-01 | Conflict Detection Agent runs within 60 seconds of ingestion completing |
| AC-F3-02 | LLM classification uses JSON mode (structured output) — no free-text parsing |
| AC-F3-03 | Binary triage keystroke → graph mutation cycle < 200ms (optimistic) |
| AC-F3-04 | Conversational clarification sends user text to LLM → structured graph commands |
| AC-F3-05 | Auto-resolution writes audit log: conflict_id, resolution_type=AUTO, timestamp |
| AC-F3-06 | Undo reverses Neo4j graph mutation atomically (transaction, no partial state) |
| AC-F3-07 | Tenant isolation: conflict scan NEVER returns another user's memories as candidates |
| AC-F3-08 | Max 5 conflicts per ingestion batch (cap enforced in conflict_worker) |
| AC-F3-09 | Empty inbox state: "All clear! ✓" with animation |

---

## Edge Cases

| Scenario | Handling |
|---|---|
| User uploads 500-page book with 100+ potential conflicts | Cap at 5 conflicts; remaining marked "deferred" and processed over next 24 hours |
| Both conflicting memories are from the same source | Skip — source-internal contradictions are editorial, not knowledge conflicts |
| AI confidence < 0.70 | Skip entirely — not surfaced in Inbox |
| User resolves conflict while API call is in-flight | Queue the second action; UI shows loading state |
| Undo after 30-second window | Return 409 Conflict with clear message |
| Network failure during optimistic update | Revert UI state + show error toast with retry option |
