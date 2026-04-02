# MemoryInbox

> **Component ID:** FE-COMP-05
> **Epic:** EPIC-04 — Conflict Detection & Memory Inbox
> **Stories:** STORY-014
> **Type:** Frontend (Dashboard)

---

## Purpose

The Memory Inbox is Ravenbase's signature differentiator — a keyboard-first interface for resolving contradictory facts surfaced by the Conflict Detection Agent. Memory is never silently overwritten; users explicitly approve or reject AI-proposed resolutions. The inbox handles three resolution flows and is designed to clear all pending conflicts in under 60 seconds. Accessible at `/inbox`.

---

## User Journey

**Viewing conflicts:**
1. After ingestion: conflict detection runs automatically (ARQ worker, runs 60s after ingestion)
2. Sidebar badge shows red count badge when `conflicts.count > 0` (polling every 30s)
3. User navigates to `/inbox`
4. Conflict cards sorted by confidence score (highest → most certain contradictions first)

**Flow 1 — Binary Triage (keyboard):**
1. `J`/`K` → navigate between cards (focus moves with visual `border-2 border-primary`)
2. `Enter` → ACCEPT_NEW (keep newer memory, mark old as superseded)
3. `Backspace` → KEEP_OLD (dismiss challenger, keep incumbent)
4. Card animates out immediately (optimistic update)
5. `POST /v1/conflicts/{id}/resolve {action: "ACCEPT_NEW" | "KEEP_OLD"}` fires in background
6. On API failure: card animates back in + error toast + state rollback

**Flow 2 — Conversational Clarification:**
1. Press `C` on any card → card expands with inline chat
2. User types free text about the conflict (e.g., "The newer one is wrong — I moved away from MySQL")
3. Press `Enter` → `POST /v1/conflicts/{id}/resolve {action: "CUSTOM", custom_text: "..."}`
4. `Escape` → collapses back to binary triage mode without resolving

**Flow 3 — Auto-Resolved with Undo:**
1. Low-confidence conflicts auto-resolve server-side during conflict scan
2. Client shows sonner toast: "Updated [resolution]. Undo?" with 30-second countdown
3. Clicking "Undo" → `POST /v1/conflicts/{id}/undo`
4. After 30s: toast dismisses, resolution is permanent (API returns 409 if undo attempted)

**All resolved:**
1. Last conflict resolved → animated checkmark `◆ ALL_CLEAR`
2. Copy: "All clear! Your knowledge graph is consistent."
3. Sidebar badge disappears

**Testing conflicts manually:**
```
/ingest I use Postgres for all new projects     (via Omnibar)
/ingest I use MySQL for all new projects        (via Omnibar)
→ similarity scan detects contradiction within ~60s → conflict appears in inbox
```

---

## Subcomponents

```
components/domain/
  MemoryInbox.tsx       — Main container with keyboard handler + state machine
  ConflictCard.tsx      — Individual card (binary + expanded chat states)
  ConflictChat.tsx      — Inline chat for Flow 2 CUSTOM resolution
  ConflictBadge.tsx     — Sidebar count badge (polls every 30s)

hooks/
  use-keyboard-inbox.ts   — J/K/Enter/Backspace/C/? keyboard handler
  use-optimistic-action.ts — Optimistic update with rollback

app/(dashboard)/inbox/
  page.tsx             — Inbox page layout
  loading.tsx          — Skeleton loading state
```

---

## API Contracts

```
GET /v1/conflicts?status=pending&limit=50
  Response: { conflicts: [...], total: number }
  Auth:     Required
  Sort:     confidence DESC (highest confidence first)

GET /v1/conflicts/count?status=pending
  Response: { count: number }
  Auth:     Required
  Used by:  Sidebar badge (polled every 30s via staleTime: 30_000)

POST /v1/conflicts/{id}/resolve
  Request:  { action: "ACCEPT_NEW" | "KEEP_OLD" | "CUSTOM", custom_text?: string }
  Response: { status: "resolved", resolution_id: string }
  Auth:     Required
  Cost:     0 credits

POST /v1/conflicts/{id}/undo
  Response: 200 OK if within 30s window
  Response: 409 CONFLICT if 30s window expired
  Auth:     Required
```

---

## Admin Bypass

No credits consumed in conflict resolution — admin bypass not needed.

Testing: seed conflicts via Omnibar (see User Journey above). Admin users can test the full conflict flow without any special handling.

---

## Design System Rules

Cross-reference: `docs/design/AGENT_DESIGN_PREAMBLE.md` (READ FIRST)
Cross-reference: `docs/design/04-ux-patterns.md` — Empty state patterns

Specific rules:
- **Active card:** `border-2 border-primary shadow-lg` (forest green `#2d4a3e`)
- **Inactive cards:** `border border-border opacity-70`
- **Confidence badge:** `bg-warning text-(--warning-foreground)` — NEVER `text-white` on amber background
- **OLD memory block:** `bg-secondary/50 rounded-lg p-4`
- **NEW memory block:** `bg-primary/10 rounded-lg border border-primary/20 p-4`
- **AI suggestion block:** `bg-accent/30 rounded-lg p-4`
- **Action buttons mobile:** `h-11` minimum tap height (RULE-11)
- **Keyboard hints:** `hidden md:flex` — desktop only
- **Empty state:** animated checkmark + `font-serif` message

---

## Known Bugs / Current State

**BUG-028 (MEDIUM):** `MemoryInbox.tsx` — `activeIndex` can go out of bounds after resolving the last conflict.
- **Root cause:** `components/domain/MemoryInbox.tsx:149-151` — after resolving the last item, `activeIndex` may still be `0` or `1` but the array is now empty. Accessing `conflicts[activeIndex]` returns `undefined` → render crash.
- **Fix:** After each resolution, clamp `activeIndex` to `Math.min(activeIndex, Math.max(0, newConflicts.length - 1))`.
- **Story:** STORY-039

**Note:** Route in existing docs says `/dashboard/inbox` — WRONG. Correct URL is `/inbox`.

---

## Acceptance Criteria

- [ ] `/inbox` renders with pending conflicts (if any exist) or empty state
- [ ] `J`/`K` navigates between cards — active card gets `border-2 border-primary`
- [ ] `Enter` on active card → `POST .../resolve {action: "ACCEPT_NEW"}` → card animates out
- [ ] `Backspace` on active card → `POST .../resolve {action: "KEEP_OLD"}` → card animates out
- [ ] `C` on active card → card expands with chat input
- [ ] Chat `Enter` → `POST .../resolve {action: "CUSTOM", custom_text: "..."}` → card animates out
- [ ] `Escape` in chat mode → collapses back to binary triage
- [ ] API failure during resolve → card animates BACK IN + error toast (optimistic rollback)
- [ ] Sidebar shows conflict count badge (polling every 30s)
- [ ] Last conflict resolved → `◆ ALL_CLEAR` empty state shown
- [ ] `activeIndex` never goes out of bounds after last card resolves
- [ ] Mobile (375px): full-width cards, action buttons `h-11`, keyboard hints hidden

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `docs/design/04-ux-patterns.md` — empty state patterns, optimistic update patterns
- `BE-COMP-02-GraphEngine.md` — conflict detection worker, conflict resolution API
- `docs/architecture/03-api-contract.md` — conflict endpoints
- `docs/components/REFACTOR_PLAN.md` — BUG-028 fix details

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-014](docs/stories/EPIC-04-conflict/STORY-014.md) | Memory Inbox UI | Frontend | Inbox with all 3 resolution flows |
| [STORY-012](docs/stories/EPIC-04-conflict/STORY-012.md) | Conflict Detection Worker | Backend | Scans for contradictions after ingestion |
| [STORY-013](docs/stories/EPIC-04-conflict/STORY-013.md) | Conflict Resolution API | Backend | Resolve, undo, status endpoints |

---

## State Machine

```
IDLE → TRIAGE
TRIAGE → (J/K) → NEXT_CARD / PREV_CARD
TRIAGE → (Enter) → RESOLVING → DONE
TRIAGE → (C) → CHAT_MODE
CHAT_MODE → (Enter with text) → RESOLVING → DONE
TRIAGE → (Backspace) → RESOLVING → DONE
CHAT_MODE → (Esc) → TRIAGE
RESOLVING → (API failure) → TRIAGE (with rollback)
DONE → (all resolved) → EMPTY_STATE
```

## Keyboard Hook Pattern

```tsx
// hooks/use-keyboard-inbox.ts
export function useKeyboardInbox(onAction: (action: InboxAction) => void, enabled: boolean) {
  useEffect(() => {
    if (!enabled) return
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      switch (e.key) {
        case "j": case "ArrowDown":  e.preventDefault(); onAction("next"); break
        case "k": case "ArrowUp":    e.preventDefault(); onAction("prev"); break
        case "Enter":               e.preventDefault(); onAction("accept"); break
        case "Backspace":           e.preventDefault(); onAction("reject"); break
        case "c": case "C":        onAction("chat"); break
        case "?":                   onAction("help"); break
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [enabled, onAction])
}
```

## ConflictCard Pattern

```tsx
// components/domain/ConflictCard.tsx
export function ConflictCard({ conflict, isActive, onAccept, onReject, onChat }: ConflictCardProps) {
  return (
    <article className={`bg-card border rounded-2xl p-6 transition-all
      ${isActive ? "border-2 border-primary shadow-lg" : "border-border opacity-70"}`}>
      <div className="flex justify-between items-start mb-4">
        <span className="font-mono text-xs tracking-wider text-muted-foreground">◆ MEMORY_CONFLICT</span>
        <span className="bg-warning text-(--warning-foreground) text-xs px-2 py-0.5 rounded-full font-mono">
          {Math.round(conflict.confidence * 100)}%
        </span>
      </div>
      <div className="bg-secondary/50 rounded-lg p-4 mb-3">
        <p className="text-xs font-mono text-muted-foreground mb-1">OLD</p>
        <p className="text-sm">{conflict.incumbent_text}</p>
      </div>
      <div className="bg-primary/10 rounded-lg border border-primary/20 p-4 mb-3">
        <p className="text-xs font-mono text-primary mb-1">NEW</p>
        <p className="text-sm">{conflict.challenger_text}</p>
      </div>
      <div className="bg-accent/30 rounded-lg p-4 mb-4">
        <p className="text-xs font-mono text-muted-foreground mb-1">◆ AI_SUGGESTION</p>
        <p className="text-sm italic">{conflict.ai_resolution}</p>
      </div>
      <div className="flex flex-col sm:flex-row gap-2">
        <Button size="sm" className="flex-1 h-11 sm:h-8 rounded-full" onClick={onAccept}>Accept New</Button>
        <Button size="sm" variant="outline" className="flex-1 h-11 sm:h-8 rounded-full" onClick={onReject}>Keep Old</Button>
        <Button size="sm" variant="secondary" className="h-11 sm:h-8 rounded-full" onClick={onChat}>Discuss</Button>
      </div>
      <div className="hidden md:flex items-center gap-2 mt-3 text-xs text-muted-foreground">
        <Kbd>J</Kbd><Kbd>K</Kbd> navigate · <Kbd>Enter</Kbd> accept · <Kbd>Backspace</Kbd> keep · <Kbd>C</Kbd> discuss
      </div>
    </article>
  )
}
```

## Conflict Badge Pattern (Sidebar)

```tsx
// components/domain/ConflictBadge.tsx
function ConflictBadge() {
  const apiFetch = useApiFetch()
  const { data } = useQuery({
    queryKey: ["conflicts", "pending-count"],
    queryFn: () => apiFetch<{ count: number }>("/v1/conflicts/count?status=pending"),
    refetchInterval: 30_000,
    staleTime: 15_000,
  })
  if (!data?.count) return null
  return (
    <span className="absolute -top-1 -right-1 bg-warning text-(--warning-foreground)
                     text-[10px] font-mono font-bold rounded-full w-4 h-4 flex items-center justify-center">
      {data.count > 9 ? "9+" : data.count}
    </span>
  )
}
```
