# STORY-014: Memory Inbox UI (Keyboard Navigation + 3 Flows)

**Epic:** EPIC-04 — Conflict Detection & Memory Inbox
**Priority:** P0
**Complexity:** Large
**Depends on:** STORY-013

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (apiFetch, no form tags, Tailwind only)
> 3. `docs/prd/03-feature-specs/F3-memory-inbox.md` — 3 UX flows (Binary Triage, Conversational, Auto-resolved)
> 4. `docs/design/04-ux-patterns.md` — keyboard navigation patterns, animations
> 5. `docs/design/02-component-library.md` — shadcn components (Card, Toast, Badge)

---

## User Story
As a user, I want to review and resolve conflicts from a keyboard-navigable inbox so that I can clear my Memory Inbox in under 60 seconds.

## Context
- Feature spec: `prd/03-feature-specs/F3-memory-inbox.md` — 3 UX flows
- Design: `design/04-ux-patterns.md` — keyboard navigation, animations
- API: STORY-013 endpoints (`GET /v1/conflicts`, `POST /v1/conflicts/{id}/resolve`, `POST /v1/conflicts/{id}/undo`)

## Acceptance Criteria
- [ ] AC-1: Memory Inbox accessible at `/dashboard/inbox`
- [ ] AC-2: **Flow 1 (Binary Triage):** J/K cycles through conflicts, Enter accepts AI resolution, Backspace rejects (keep old), all with < 200ms UI update
- [ ] AC-3: **Flow 2 (Conversational):** C key expands active card to inline chat; typing custom text and pressing Enter calls `CUSTOM` resolve action
- [ ] AC-4: **Flow 3 (Auto-resolved):** Auto-resolved conflicts appear as toast "Updated [X]. Undo?" with 30-second countdown
- [ ] AC-5: Conflict count badge shows on sidebar nav icon (updates in real-time via SSE or polling)
- [ ] AC-6: Conflict card shows: incumbent text, challenger text, AI proposed resolution, source filenames, confidence score badge
- [ ] AC-7: After resolving last conflict: empty state "All clear! Your knowledge graph is up to date." with checkmark animation
- [ ] AC-8: Optimistic UI: action appears to complete instantly (< 100ms) before API confirms
- [ ] AC-9: If API call fails after optimistic update: show error toast and revert UI state
- [ ] AC-10: Accessible: all keyboard shortcuts listed in tooltip on `?` keypress
- [ ] AC-11: Mobile (< 768px): conflict cards are full-width; action buttons expand to a
  full-width row with minimum 44px tap height; keyboard shortcut hints hidden on mobile
- [ ] AC-12: Mobile (< 768px): swipe-right gesture triggers Accept, swipe-left triggers
  Keep Old as a progressive enhancement (visible button row is the baseline)

## Technical Notes

### Files to Create (Frontend)
- `components/domain/MemoryInbox.tsx` — main container with keyboard handler
- `components/domain/ConflictCard.tsx` — individual conflict card (binary + expanded view)
- `components/domain/ConflictChat.tsx` — inline chat for Flow 2 (CUSTOM resolve)
- `hooks/use-keyboard-inbox.ts` — J/K/Enter/Backspace/C keyboard handler
- `app/(dashboard)/inbox/page.tsx` — page layout

### Visual Styling Reference

The ConflictCard visual patterns are defined in the design system — read these before implementing:
- `docs/design/01-design-system.md` → **Section A: Conflict Card (Active)** — full TSX with `border-2 border-primary`, OLD in `bg-secondary/50`, NEW in `bg-primary/10`, AI suggestion in `bg-accent/30`
- `docs/design/01-design-system.md` → **Section B: Memory Sticky Note** — `bg-[#fef9c3]` rotation pattern
- `docs/design/02-component-library.md` → **`<ConflictCard />`** section — interface definition and visual anatomy

Key classes for ConflictCard states:
- Active card: `border-2 border-primary` (not `shadow-lg`)
- Inactive card: `border border-border opacity-70`
- Confidence badge: `bg-warning text-[var(--warning-foreground)]`
- OLD memory row: `bg-secondary/50 rounded-lg`
- NEW memory row: `bg-primary/10 rounded-lg border border-primary/20`
- AI suggestion panel: `bg-accent/30 rounded-lg`

### Mobile Layout

On mobile, the inbox shifts from centered-card layout to full-width stacked cards.
The keyboard shortcut hints (`<Kbd>`) are hidden with `hidden md:flex`.
Action buttons expand to full-width row with 44px minimum touch targets:

```tsx
{/* Mobile: full-width button row; Desktop: inline buttons */}
<div className="flex flex-col sm:flex-row gap-2">
  <Button size="sm" className="flex-1 h-11 sm:h-8">Accept New</Button>
  <Button size="sm" variant="outline" className="flex-1 h-11 sm:h-8">Keep Old</Button>
  <Button size="sm" variant="secondary" className="h-11 sm:h-8">Discuss</Button>
</div>
{/* Keyboard hints only on desktop */}
<div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
  <Kbd>Enter</Kbd> <Kbd>Backspace</Kbd> <Kbd>C</Kbd>
</div>
```

### Architecture Constraints
- No `<form>` tags — ConflictChat uses controlled input + onClick
- All API calls via `apiFetch` — never raw `fetch()`
- Optimistic update: update local state immediately, revert on API error
- Keyboard events on `window` level (`addEventListener`) — not on individual elements
- Toast for auto-resolved uses shadcn `useToast` hook with 30-second countdown

### State Machine
```
IDLE → (user opens inbox) → TRIAGE
TRIAGE → (J/K) → NEXT_CARD
TRIAGE → (Enter) → RESOLVING → DONE (with undo toast)
TRIAGE → (C) → CHAT_MODE
CHAT_MODE → (Enter with text) → RESOLVING → DONE
TRIAGE → (Backspace) → RESOLVING → DONE
```

### Keyboard Hook Pattern
```typescript
// hooks/use-keyboard-inbox.ts
import { useEffect } from "react";

interface KeyboardInboxOptions {
  onNext: () => void;
  onPrev: () => void;
  onAccept: () => void;
  onReject: () => void;
  onChat: () => void;
  onHelp: () => void;
  disabled?: boolean;
}

export function useKeyboardInbox({
  onNext, onPrev, onAccept, onReject, onChat, onHelp, disabled,
}: KeyboardInboxOptions) {
  useEffect(() => {
    if (disabled) return;
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return; // ignore when typing
      switch (e.key) {
        case "j": onNext(); break;
        case "k": onPrev(); break;
        case "Enter": onAccept(); break;
        case "Backspace": onReject(); break;
        case "c": onChat(); break;
        case "?": onHelp(); break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onNext, onPrev, onAccept, onReject, onChat, onHelp, disabled]);
}
```

### Optimistic Update Pattern
```typescript
// In MemoryInbox.tsx — optimistic resolution
const handleResolve = async (action: "ACCEPT_NEW" | "KEEP_OLD") => {
  const conflictId = conflicts[activeIndex].id;
  // 1. Optimistic: remove from list immediately
  setConflicts((prev) => prev.filter((c) => c.id !== conflictId));

  try {
    await apiFetch(`/v1/conflicts/${conflictId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
  } catch {
    // 2. Revert on failure
    setConflicts((prev) => [...prev, conflicts[activeIndex]]);
    toast({ title: "Failed to resolve conflict. Please try again.", variant: "destructive" });
  }
};
```

## Definition of Done
- [ ] All 3 flows work end-to-end with real API
- [ ] Keyboard shortcuts work without mouse
- [ ] Optimistic updates function correctly (including rollback on failure)
- [ ] Conflict count badge updates in sidebar
- [ ] Empty state renders after last conflict resolved
- [ ] `npm run build` passes (no TypeScript errors)

## Testing This Story

```bash
# Frontend build check:
npm run build

# Manual test (requires seeded conflict data):
# 1. uv run python scripts/seed_dev_data.py (seed 3+ conflicts)
# 2. Open http://localhost:3000/dashboard/inbox
# 3. Press J — move to next conflict
# 4. Press K — move to previous conflict
# 5. Press Enter — resolve with ACCEPT_NEW (verify optimistic update + API call)
# 6. Press Backspace — resolve with KEEP_OLD
# 7. Press C — expand chat mode, type custom text, press Enter
# 8. Resolve all — verify empty state renders
# 9. Disconnect network mid-resolve — verify rollback toast
```

**Passing result:** All 3 flows work via keyboard. Optimistic UI resolves < 100ms. Rollback on failure. Empty state after all resolved.

---

## Agent Implementation Brief

```
Implement STORY-014: Memory Inbox UI (Keyboard Navigation + 3 Flows).

Read first:
1. CLAUDE.md (architecture rules)
2. docs/design/CLAUDE_FRONTEND.md (no form tags, apiFetch, Tailwind only)
3. docs/prd/03-feature-specs/F3-memory-inbox.md (3 flows: Binary Triage, Conversational, Auto-resolved)
4. docs/design/04-ux-patterns.md (keyboard navigation patterns)
5. docs/stories/EPIC-04-conflict/STORY-014.md (this file)

Key constraints:
- No <form> tags — ConflictChat uses div + onClick + controlled input
- Keyboard events on window level (not element-level) via useKeyboardInbox hook
- Optimistic update: update state FIRST, revert on apiFetch failure
- Auto-resolved toast uses shadcn useToast with 30-second countdown timer
- Conflict count badge in sidebar polls GET /v1/conflicts?status=pending (or SSE)

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
git add -A && git commit -m "feat(ravenbase): STORY-014 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-014"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-014
git add docs/stories/epics.md && git commit -m "docs: mark STORY-014 complete"
```
