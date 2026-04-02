# Design — 04. UX Patterns & Interaction Design

> **Cross-references:** `design/02-component-library.md` | `prd/03-feature-specs/F3-memory-inbox.md`

---

## Core UX Principles

1. **Speed is a feature** — Every interaction should feel instant (<100ms perceived). Use optimistic updates everywhere.
2. **Keyboard-first for power users** — All critical workflows completable without mouse.
3. **Progressive disclosure** — Complex features (Graph Explorer, conflict resolution) start simple, depth available on demand.
4. **Zero data loss UX** — Every destructive action has an undo (with time-bounded window).
5. **Observable system** — Users always know what's happening: progress bars, status badges, loading skeletons.

---

## Optimistic Update Pattern

Used throughout the app for low-latency interactions:

```tsx
// Pattern: Update UI immediately, then confirm with API.
// On failure: revert + show error toast.

// hooks/use-optimistic-action.ts
import { useState } from "react";
import { toast } from "sonner";

export function useOptimisticAction<T>(
  optimisticUpdate: () => T,
  apiCall: () => Promise<void>,
  rollback: (prev: T) => void,
) {
  const [isPending, setIsPending] = useState(false);

  const execute = async () => {
    const prevState = optimisticUpdate(); // Update UI immediately
    setIsPending(true);
    try {
      await apiCall();
    } catch (err) {
      rollback(prevState); // Revert on failure
      toast.error("Action failed. Please try again.");
    } finally {
      setIsPending(false);
    }
  };

  return { execute, isPending };
}
```

**Applied in:** Memory Inbox triage, conflict resolution, profile switching.

---

## Button Loading State Pattern

Every button that triggers an API call or async operation must follow this pattern.
This applies to: form submits, settings saves, conflict resolutions, generation triggers,
credit top-ups, any action that takes > 0ms to complete.

**Rule:** Disable the button AND change its text while the call is in flight.
Never leave a button clickable while its action is pending.

```tsx
// hooks/use-async-button.ts
// Reusable hook for any button that triggers an async action
import { useState } from "react";
import { toast } from "sonner";

interface AsyncButtonOptions {
  onSuccess?: () => void;
  successMessage?: string;
  errorMessage?: string;
}

export function useAsyncButton(
  action: () => Promise<void>,
  options: AsyncButtonOptions = {},
) {
  const [isLoading, setIsLoading] = useState(false);

  const trigger = async () => {
    if (isLoading) return; // Prevent double-submit
    setIsLoading(true);
    try {
      await action();
      if (options.successMessage) {
        toast.success(options.successMessage);
      }
      options.onSuccess?.();
    } catch {
      toast.error(options.errorMessage ?? "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return { trigger, isLoading };
}
```

```tsx
// Usage pattern — apply consistently across all async buttons
import { useAsyncButton } from "@/hooks/use-async-button";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

function SaveSettingsButton({ onSave }: { onSave: () => Promise<void> }) {
  const { trigger, isLoading } = useAsyncButton(onSave, {
    successMessage: "Settings saved",
  });

  return (
    <Button onClick={trigger} disabled={isLoading}>
      {isLoading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Saving…
        </>
      ) : (
        "Save changes"
      )}
    </Button>
  );
}
```

**Label pairs (use consistently):**

| Default label | Loading label |
|---|---|
| Save changes | Saving… |
| Generate | Generating… |
| Upload | Uploading… |
| Export | Exporting… |
| Delete | Deleting… |
| Submit | Submitting… |
| Connect | Connecting… |
| Apply | Applying… |

**When NOT to use this pattern:**
- Optimistic actions (conflict triage J/K/Enter) — already instant, use `useOptimisticAction`
- Navigation links — use Next.js loading.tsx instead
- Toggle switches — use `useOptimisticAction` with immediate flip

---

## Keyboard Navigation System

### Dashboard Global Shortcuts

| Shortcut | Action |
|---|---|
| `/` | Focus Omnibar |
| `⌘K` / `Ctrl+K` | Open command palette |
| `⌘G` | Go to Graph Explorer |
| `⌘I` | Go to Inbox |
| `⌘W` | Go to Workstation |
| `⌘,` | Go to Settings |
| `?` | Show keyboard shortcut reference |

### Memory Inbox Shortcuts

| Shortcut | Action |
|---|---|
| `J` | Next conflict |
| `K` | Previous conflict |
| `Enter` | Accept AI resolution (ACCEPT_NEW) |
| `Backspace` | Keep old memory (KEEP_OLD) |
| `C` | Enter conversational mode |
| `Esc` | Exit conversational mode |
| `?` | Show shortcut reference |

### Graph Explorer Shortcuts

| Shortcut | Action |
|---|---|
| `+` / `-` | Zoom in/out |
| `F` | Fit all nodes to screen |
| `Esc` | Close node detail panel |
| `←/→` | Pan graph |

### Implementation

```tsx
// hooks/use-keyboard-inbox.ts
import { useEffect } from "react";

type InboxAction = "next" | "prev" | "accept" | "reject" | "chat" | "help";

export function useKeyboardInbox(
  onAction: (action: InboxAction) => void,
  enabled: boolean,
) {
  useEffect(() => {
    if (!enabled) return;

    const handler = (e: KeyboardEvent) => {
      // Don't fire when user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case "j": case "ArrowDown": onAction("next"); break;
        case "k": case "ArrowUp":   onAction("prev"); break;
        case "Enter":               onAction("accept"); e.preventDefault(); break;
        case "Backspace":           onAction("reject"); e.preventDefault(); break;
        case "c": case "C":        onAction("chat"); break;
        case "?":                   onAction("help"); break;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [enabled, onAction]);
}
```

---

## Loading & Skeleton States

Every data-fetching component has a skeleton state. Never show blank areas.

```tsx
// Pattern: skeleton while loading, content when ready
// Using shadcn Skeleton component

// ConflictCard skeleton
function ConflictCardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      <div className="flex justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Separator />
      <Skeleton className="h-4 w-1/2" />
    </div>
  );
}
```

---

## Notification Fatigue Prevention

Memory Inbox notifications are batched and non-intrusive:

1. **Badge count only** — The sidebar icon shows a count. No push notifications, no modal interruptions.
2. **Batch delivery** — All conflicts from one ingestion surfaced together, not one-by-one.
3. **Batching cap** — Maximum 5 conflicts per ingestion batch (configurable in conflict_worker).
4. **Natural timing** — Conflicts surfaced when user opens the app, not mid-task.
5. **Dismissible** — "Mark all as seen" option that sets conflicts to `dismissed` without resolving.

---

## First-Run Dashboard Experience

The dashboard has three distinct first-run states depending on how the user arrived.
These must be handled at the `/dashboard` page level (not inside individual components).

### State 1 — Arrived via onboarding WITH upload (most common)

The user just completed the wizard and uploaded their first file. Processing is happening.
The graph is empty while Docling and entity extraction run (typically 10–120 seconds).

```tsx
// app/(dashboard)/page.tsx — detect first-run via URL query param
// After completing onboarding, the wizard appends ?first_run=true to the redirect:
// router.push("/chat?first_run=true")
// This param is read once, then removed from the URL via router.replace

// The GettingStartedChecklist renders if:
// 1. URL has ?first_run=true, OR
// 2. user.has_completed_onboarding is true AND sources.length === 0 AND
//    checklist not dismissed in localStorage

// Show the checklist in the sidebar below the nav items:
<GettingStartedChecklist />

// In the main content area (Graph Explorer position), while processing:
<div className="flex flex-col items-center justify-center h-full gap-4">
  <RavenbaseLogo size="lg" className="opacity-20 animate-pulse" />
  <p className="font-mono text-xs tracking-wider text-muted-foreground">
    ◆ BUILDING_GRAPH
  </p>
  <p className="text-muted-foreground text-sm max-w-xs text-center">
    Ravenbase is processing your file and extracting memories.
    This takes 10–120 seconds.
  </p>
  <p className="font-mono text-xs text-muted-foreground">
    You can close this tab — it will continue in the background.
  </p>
</div>
```

### State 2 — Arrived via "Skip for now" (no upload)

The user skipped the upload step. The graph is empty with no processing happening.

```tsx
// Render a purposeful empty state — not just a blank graph
<div className="flex flex-col items-center justify-center h-full gap-6 p-8">
  <RavenbaseLogo size="xl" className="opacity-15" />
  <div className="text-center max-w-sm">
    <p className="font-mono text-xs tracking-wider text-muted-foreground mb-3">
      ◆ NO_MEMORIES_YET
    </p>
    <h2 className="font-serif text-3xl mb-3">Start building your memory</h2>
    <p className="text-muted-foreground text-sm leading-relaxed mb-6">
      Upload your first notes, chat exports, or documents.
      Ravenbase will extract your knowledge automatically.
    </p>
    <Button size="lg" onClick={() => openIngestionDropzone()}>
      Upload your first file
    </Button>
    <p className="text-xs text-muted-foreground mt-4">
      Or paste text directly using the Omnibar below (⌘K)
    </p>
  </div>
</div>
```

### State 3 — Returning user, graph is empty (deleted everything)

Same as State 2 but without onboarding framing. The GettingStartedChecklist does not show.
The empty state copy changes to:
```
"Your knowledge graph is empty. Upload a file or capture a thought to rebuild it."
```

### The GettingStartedChecklist Component

A lightweight, persistent checklist anchored in the sidebar below the navigation.
Auto-dismisses when all 3 items are checked. User can also manually dismiss it.
Dismissed state stored in `localStorage` key `ravenbase-checklist-dismissed`.

```tsx
// components/domain/GettingStartedChecklist.tsx
// This is a sidebar widget, NOT a modal or a product tour.
// It never interrupts the user — it just lives quietly in the sidebar.

const CHECKLIST_KEY = "ravenbase-checklist-dismissed"

const steps = [
  {
    id: "upload",
    label: "Upload your first file",
    // completed when: sources.length > 0
    href: null,  // triggers ingestion dropzone
  },
  {
    id: "graph",
    label: "Explore your knowledge graph",
    // completed when: user has navigated to /graph
    href: "/graph",
  },
  {
    id: "ask",
    label: "Ask your first question",
    // completed when: chat_sessions.length > 0
    href: "/chat",
  },
]

// Renders as a small collapsible card at the bottom of the sidebar:
// ┌─────────────────────────────────┐
// │ ◆ GETTING STARTED          [×] │
// │ ■ Upload your first file    ✓  │
// │ □ Explore your graph           │
// │ □ Ask your first question      │
// │ ▓▓▓▓▓░░░░░░░░░ 1/3             │
// └─────────────────────────────────┘

// The [×] dismiss button stores ravenbase-checklist-dismissed=true in localStorage.
// The checklist auto-dismisses (with a 1-second fade animation) when all 3 are checked.
// NEVER show this checklist again after it has been dismissed.
```

### Rules for the first-run experience

- `?first_run=true` query param is appended by the onboarding wizard on redirect. Remove it from the URL immediately with `router.replace` after reading it — do not leave it in the URL bar.
- The GettingStartedChecklist shows only if: (a) first_run param was present, OR (b) `user.sources_count === 0` AND the checklist has not been dismissed. Once sources exist AND checklist is dismissed, it is gone permanently.
- Never show the checklist in a modal. Never auto-play a product tour. Never show a video. The checklist is ambient — it helps; it does not demand.
- All three completion checks use data already fetched for the dashboard — no additional API calls for checklist state.

---

## Empty States

Every list/collection has a purposeful empty state:

| Location | Empty State |
|---|---|
| Graph Explorer | Illustrated graph mockup + "Upload your first file to start building your knowledge graph" + [Upload button] |
| Memory Inbox | Checkmark animation + "All clear! Your knowledge graph is fully up to date." |
| Workstation history | "No documents yet. Generate your first Meta-Document above." |
| Sources list | Dropzone + "Drop your first file to get started." |
| Search results | "No results for '[query]'. Try different keywords or [upload more content]." |

Empty states always include a call-to-action that helps the user resolve the emptiness.

---

## Error States

| Error Type | UI Treatment |
|---|---|
| API error (network) | Toast: "Connection error. Check your internet." + retry button |
| API error (server 5xx) | Toast: "Something went wrong. Our team has been notified." |
| File upload fail | Inline error under dropzone with specific reason |
| Generation timeout | Workstation: "Generation timed out. Try a shorter prompt or retry." + retry button |
| Insufficient credits | Modal with upgrade prompt + credits balance + top-up button |
| Auth expired | Redirect to login with "Your session expired. Please sign in again." |

---

## Progress Indicators

Hierarchy of progress communication:
1. **Immediate (<1s):** No indicator — feels instant
2. **Short (1-5s):** Spinner or pulsing skeleton
3. **Medium (5-30s):** Determinate progress bar with percentage and status message
4. **Long (30s-5min):** Progress bar + expandable detail log + "Email me when done" option (post-MVP)

```tsx
// Ingestion progress bar component
<div className="space-y-2">
  <div className="flex justify-between text-xs font-mono text-muted-foreground">
    <span>{statusMessage}</span>
    <span>{progressPct}%</span>
  </div>
  <Progress value={progressPct} className="h-1.5" />
</div>
```

---

## Destructive Action Undo Pattern

Core UX Principle #4 states: "Every destructive action has a time-bounded undo."
This section specifies exactly how to implement it.

**The pattern:** Destructive actions (delete source, delete profile, delete meta-document)
do NOT fire the API call immediately. Instead:
1. Show a sonner toast with the item name, "Undo" button, and a 5-second countdown
2. Start a 5-second timer (managed by `useRef` — survives re-renders)
3. If the user clicks Undo → cancel the timer, remove the toast, restore the item optimistically
4. If the timer expires → fire the actual `DELETE` API call

This creates the feeling of instant deletion (optimistic removal from UI) while giving users
a 5-second safety window — without requiring a confirmation dialog.

### When to use this pattern

| Action | Use undo toast | Use confirmation dialog instead |
|---|---|---|
| Delete a source file | ✅ Undo toast (5 seconds) | — |
| Delete a Meta-Document | ✅ Undo toast (5 seconds) | — |
| Delete a System Profile | — | ✅ Dialog (profile + all its memories are deleted) |
| Delete account (GDPR) | — | ✅ Dialog (irreversible, too severe for toast) |

**Rule of thumb:** Use the undo toast for items the user might delete by accident (file, document).
Use a confirmation dialog for actions that delete large amounts of data or are truly irreversible.

### Implementation pattern

```tsx
// hooks/useDestructiveAction.ts
// Reusable hook — use this for every delete in the codebase
import { useRef } from "react"
import { toast } from "sonner"

interface UseDestructiveActionOptions {
  itemLabel: string              // e.g. "meeting-notes.pdf" or "Work Profile"
  onConfirmed: () => Promise<void>  // The actual DELETE API call
  onUndo?: () => void            // Optional: restore optimistic state
  delayMs?: number               // Default: 5000ms
}

export function useDestructiveAction() {
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  const trigger = ({
    itemLabel,
    onConfirmed,
    onUndo,
    delayMs = 5000,
  }: UseDestructiveActionOptions) => {
    // 1. Clear any pending timer (user triggered two deletes quickly)
    clearTimeout(timerRef.current)

    // 2. Show toast immediately
    const toastId = toast(
      <div className="flex items-center justify-between w-full gap-4">
        <span className="text-sm">
          <span className="font-medium">{itemLabel}</span> deleted
        </span>
        <button
          onClick={() => {
            clearTimeout(timerRef.current)
            toast.dismiss(toastId)
            onUndo?.()
          }}
          className="text-sm font-medium text-primary hover:underline shrink-0"
        >
          Undo
        </button>
      </div>,
      {
        duration: delayMs,
        // sonner supports a custom duration — the toast auto-dismisses at delayMs
      }
    )

    // 3. Set timer — fires the actual DELETE after delayMs
    timerRef.current = setTimeout(async () => {
      try {
        await onConfirmed()
      } catch (err) {
        // If DELETE fails, restore the item and show error
        onUndo?.()
        toast.error(`Failed to delete ${itemLabel}. It has been restored.`)
      }
    }, delayMs)
  }

  return { trigger }
}

// ─── Usage example: SourceCard.tsx ──────────────────────────────────────────
// import { useDestructiveAction } from "@/hooks/useDestructiveAction"
//
// const { trigger } = useDestructiveAction()
//
// const handleDelete = () => {
//   // 1. Optimistically remove from UI immediately
//   removeSourceFromList(source.id)
//
//   // 2. Trigger the undo-protected delete
//   trigger({
//     itemLabel: source.filename,
//     onConfirmed: () => apiFetch(`/v1/sources/${source.id}`, { method: "DELETE" }),
//     onUndo: () => restoreSourceToList(source),
//   })
// }
```

### Where this hook is used (agent reference)

| Story | What gets deleted | `itemLabel` |
|---|---|---|
| STORY-007-FE | Source file | `source.filename` |
| STORY-017 | Meta-Document | `doc.title` or `"Untitled document"` |

**File to create:** `hooks/useDestructiveAction.ts` (during the story that first needs it, STORY-007-FE)
**Add to STORY-001-WEB scaffold:** `hooks/` directory entry in Files to Create

---

## Toast Notification Patterns

Use `sonner` for all toasts (`import { toast } from "sonner"`). For custom inline notification banners, use the semantic variants from `design/01-design-system.md` Section 6H:

```tsx
// Success — bg-success/10 border-success/25 text-success icon
// Warning — bg-warning/10 border-warning/25 text-warning icon
// Error   — bg-destructive/10 border-destructive/25 text-destructive icon
// Info    — bg-info/10 border-info/25 text-info icon
```

**Warning color rule:** `text-warning` on `bg-warning/10` is acceptable (low contrast bg).
On solid `bg-warning` — use `text-[var(--warning-foreground)]` (dark text).

---

## Copy-to-Clipboard Pattern

Used in: STORY-028 (AI import prompt copy), STORY-034 (referral link copy),
STORY-036 (admin user ID copy), and any future "copy" action.

```tsx
// hooks/use-copy-to-clipboard.ts
import { useState, useCallback } from "react";

export function useCopyToClipboard(resetMs = 2000) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
    } catch {
      // Fallback for older browsers / insecure contexts
      const el = document.createElement("textarea");
      el.value = text;
      el.style.position = "absolute";
      el.style.opacity = "0";
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), resetMs);
    }
  }, [resetMs]);

  return { copy, copied };
}
```

```tsx
// Usage — apply consistently for all copy buttons
import { useCopyToClipboard } from "@/hooks/use-copy-to-clipboard";
import { Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const { copy, copied } = useCopyToClipboard();

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => copy(text)}
      className="gap-2"
      aria-label={copied ? "Copied to clipboard" : `${label} to clipboard`}
    >
      {copied ? (
        <>
          <Check className="h-4 w-4 text-green-600" />
          Copied ✓
        </>
      ) : (
        <>
          <Copy className="h-4 w-4" />
          {label}
        </>
      )}
    </Button>
  );
}
```

**Behaviour rules:**
- Reset to default state after **2 seconds** (never 1s — users need time to see it)
- Icon changes: `Copy` → `Check` with `text-green-600` (success signal)
- Label changes: `"Copy link"` → `"Copied ✓"` (the ✓ reinforces success)
- Button stays enabled during the "copied" state — user can re-copy immediately
- Accessible: `aria-label` updates to announce the copy action to screen readers
- Use `<Check>` from `lucide-react` (already in the project) — do not import new libraries

---

## Animation Patterns

```css
/* Memory sticky note hover — straightens on hover */
.memory-note {
  transition: transform 0.2s ease;
}
/* Applied by Tailwind: rotate-[-0.8deg] hover:rotate-0 */

/* Conflict node: animate-pulse on bg-warning/20 outer, solid bg-warning inner */
/* Use bg-warning NOT bg-amber-500 */
```

---

## Mobile-Specific Patterns

| Component | Mobile (< 768px) | Desktop (≥ 768px) |
|---|---|---|
| Sidebar | Bottom-sheet drawer (Sheet component) | Visible left rail |
| History panels (Workstation, Chat) | Bottom Sheet, toggle via header button | Left panel, always visible |
| Omnibar | `fixed bottom-0` with `safe-area-inset-bottom` | Embedded in layout |
| Memory Inbox cards | Full-width, 44px tap targets | Centered, keyboard-navigated |
| Graph Explorer | Concept list (no Cytoscape) | Force-directed graph |
| Onboarding wizard | Full-screen card | Centered card with padding |
| Conflict action buttons | Full-width row, `h-11` | Compact inline row, `h-8` |

**iOS-specific rules (apply to all sticky/fixed elements):**
- Full-height containers: `h-[100dvh]` not `h-screen`
- Sticky footers/inputs: `pb-[max(1rem,env(safe-area-inset-bottom))]`
- Touch targets: minimum `44px` height for all tappable elements
