# Design — 02. Component Library

> **Cross-references:** `design/01-design-system.md` (tokens) | `design/03-screen-flows.md` (usage in layouts)

---

## shadcn/ui Components (Pre-installed)

All from the template. Use via `@/components/ui/`. Never rebuild what shadcn provides.

### Core Components Used Per Feature

| Feature | shadcn Components |
|---|---|
| Memory Inbox | `Card`, `Badge`, `Button`, `Separator`, `Kbd`, `Progress`, `Tooltip` |
| Graph Explorer | `Sheet` (node detail panel), `Tabs`, `Badge`, `Button`, `Select` |
| Workstation | `Textarea`, `Button`, `Separator`, `ScrollArea`, `Skeleton` |
| Omnibar | `Command` (cmdk), `Dialog`, `Input` |
| Onboarding | `Tabs`, `Button`, `Progress`, `Card`, `Form`, `Input` |
| Landing page | `Button`, `Badge`, `Card`, `Separator`, `NavigationMenu` |
| Settings | `Form`, `Input`, `Select`, `Switch`, `Tabs`, `Dialog`, `AlertDialog` |
| Auth pages | `Card`, `Form`, `Input`, `Button`, `Label` |

### Sonner for Toasts

All toast notifications use `sonner` (not the legacy `toast.tsx`):

```tsx
import { toast } from "sonner";

// Success toast (conflict resolved)
toast.success("Updated primary framework to Vue.", {
  description: "React tagged as Past Skill.",
  action: { label: "Undo", onClick: handleUndo },
  duration: 30000,  // 30-second undo window
});

// Progress toast (ingestion)
const toastId = toast.loading("Indexing document...");
// Later:
toast.success("Indexed 42 chunks across 3 concepts.", { id: toastId });

// Error toast
toast.error("Upload failed", {
  description: "File exceeds 50MB limit for free accounts.",
});
```

---

## Custom Domain Components

These are Ravenbase-specific components that agents must implement. Specifications below.

---

### `<Omnibar />`

The persistent command-palette interface at the bottom of the dashboard.

```tsx
// components/domain/Omnibar.tsx
// Behavior:
// - Stays at bottom of dashboard on mobile, in sidebar on desktop
// - On "/" keypress from anywhere: focuses the input
// - Slash commands activate on typing "/" followed by command name
// - "Natural language" mode when no slash command matches

interface OmnibarProps {
  activeProfileId: string;
  onProfileSwitch: (profileId: string) => void;
}

// Slash commands:
// /ingest [text]     → quick text capture
// /search [query]    → semantic search
// /profile [name]    → switch profile
// /generate [prompt] → open workstation with prompt
// /inbox             → navigate to inbox
// /graph             → navigate to graph

// Visual: matches template's CTA rounded-pill input aesthetic
// className: "bg-secondary/50 border border-border rounded-full px-4 py-2.5
//             text-sm font-mono placeholder:text-muted-foreground w-full"
```

---

### `<ConflictCard />`

The central UI unit of the Memory Inbox.

```tsx
// components/domain/ConflictCard.tsx

interface ConflictCardProps {
  conflict: Conflict;
  isActive: boolean;
  mode: "triage" | "chat";
  onAccept: () => void;
  onReject: () => void;
  onEnterChat: () => void;
  onChatSubmit: (text: string) => void;
}

// Visual anatomy:
// ┌──────────────────────────────────────────────────────────┐
// │ [◆ MEMORY_CONFLICT]          [confidence: 94%] [source]  │
// │──────────────────────────────────────────────────────────│
// │ OLD  [incumbent text in muted style]                     │
// │ NEW  [challenger text in primary/accent style]           │
// │──────────────────────────────────────────────────────────│
// │ AI:  [proposed resolution in italic]                     │
// │──────────────────────────────────────────────────────────│
// │ [Enter → Accept]  [Backspace → Keep Old]  [C → Chat]     │
// │ from: [source1_filename] → [source2_filename]            │
// └──────────────────────────────────────────────────────────┘

// Active card: border-2 border-primary
// Inactive cards: border-border opacity-70
// Chat mode: card expands, shows inline textarea + AI prompt

// Keyboard shortcut hints use shadcn <Kbd> component:
// <Kbd>Enter</Kbd> <Kbd>↵ Accept</Kbd>
```

> **Full TSX implementation pattern:** See `design/01-design-system.md` → Section A (Conflict Card Active).
> Key classes: active card = `border-2 border-primary`, OLD row = `bg-secondary/50`, NEW row = `bg-primary/10 border border-primary/20`, AI panel = `bg-accent/30`, confidence badge = `bg-warning text-[var(--warning-foreground)]`.

---

### `<GraphExplorer />`

Force-directed graph using Cytoscape.js.

```tsx
// components/domain/GraphExplorer.tsx

// Cytoscape stylesheet:
const cytoscapeStyle = [
  {
    selector: "node[type='concept']",
    style: {
      "background-color": "#2d4a3e",  // primary green (NOT blue)
      "label": "data(label)",
      "font-size": 10,
      "color": "#ffffff",
    }
  },
  {
    selector: "node[type='memory']",
    style: { "background-color": "#e8ebe6", "shape": "round-rectangle" }  // secondary
  },
  {
    selector: "node[type='conflict']",
    style: {
      "background-color": "#ffc00d",    // warning amber (NOT #f59e0b)
      "border-width": 3,
      "border-color": "#ffc00d",
    }
  },
  {
    selector: "edge",
    style: { "line-color": "#d1d5db", "width": 1, "curve-style": "bezier" }  // border color
  },
  {
    selector: "edge[type='CONTRADICTS']",
    style: { "line-color": "#b53233", "line-style": "dashed", "width": 2 }  // destructive
  },
  {
    selector: ".query-match",
    style: {
      "background-color": "#ffc00d",  // warning amber for NL query highlights
      "border-width": 3,
      "border-color": "#d97706",
    }
  },
];

// Node click → opens <GraphNodePanel /> as a Sheet (right-side panel)
// Mobile fallback: renders as a searchable <ConceptList /> instead of graph
```

---

### `<IngestionDropzone />`

Drag-and-drop file upload area.

```tsx
// components/domain/IngestionDropzone.tsx
// Uses react-dropzone
// States: idle | dragover | uploading | processing | success | error

// Visual (from template upload component in BMAD blueprint):
// idle:       dashed border, "Drop files here or click to upload"
// dragover:   solid primary border, scale-up animation
// uploading:  spinner, "Uploading..."
// processing: <Progress /> bar, SSE-driven percentage
// success:    checkmark (check-draw animation), "Indexed 42 chunks"
// error:      red ring, error message, "Try again" link

// Accepted: PDF, TXT, MD, JSON, ZIP
// Max size shown: "50MB free / 200MB pro"
```

---

### `<MetaDocEditor />`

The streaming Markdown renderer in the Workstation.

```tsx
// components/domain/MetaDocEditor.tsx
// Receives SSE token stream and renders as Markdown in real-time

// Uses react-markdown for rendering
// Custom components: headers, code blocks, lists all styled per design system

// Streaming cursor: blinking "|" appended to last streamed character
// Fade-in each paragraph as it completes

// Toolbar:
// [Export MD]  [Export PDF]  [Sources (N)]  [Regenerate]
```

---

## Layout Components

### `<DashboardLayout />`

```tsx
// app/(dashboard)/layout.tsx
// IMPORTANT: No longer forces dark mode. Light by default.
// Dark mode only if user has toggled it (stored in localStorage, applied to <html>)
// Structure:
// <div className="flex h-screen bg-background overflow-hidden">
//   <Sidebar />       ← Forest green sidebar — bg-primary
//   <SidebarInset>    ← Main content area
//     <Header />      ← Top bar with profile switcher + search + notifications + dark toggle
//     <main>          ← Page content
//     </main>
//   </SidebarInset>
// </div>

// Sidebar items:
// - Ravenbase logo
// - [Profile switcher dropdown]
// - Graph Explorer     /dashboard/graph
// - Memory Inbox       /dashboard/inbox  [conflict badge]
// - Workstation        /dashboard/workstation
// - Sources            /dashboard/sources
// - ─────────────
// - Settings           /dashboard/settings
// - Credits [balance]  /dashboard/settings/billing
```

### `<MarketingLayout />`

```tsx
// app/(marketing)/layout.tsx
// Default light mode — no forced className="light"
// bg-background (cream #f5f3ee) — warm aged-paper feel
// Full-width with max-w-7xl containers
// Sticky header with blur backdrop
```

---

## Ravenbase-Specific Patterns (from BrandStyleGuide)

See `design/01-design-system.md` Section 6 for complete code patterns for:
- **ConflictCard (Active)** — `border-2 border-primary`, OLD in `bg-secondary/50`, NEW in `bg-primary/10`, AI in `bg-accent/30`
- **ConflictCard (Inactive)** — `border-border opacity-70`
- **Memory Sticky Note** — `bg-[#fef9c3] rotate-[-0.8deg] hover:rotate-0 transition-transform`
- **IngestionDropzone** — `border-dashed border-border hover:border-primary`
- **Dashboard Sidebar** — `bg-primary text-primary-foreground` (always green, even in dark mode)
- **Graph filter bar** — shadcn `Select` components in `bg-secondary` container
- **Workstation streaming output** — streaming cursor `▌` appended to last token

---

## Animation Patterns

From design system + BMAD blueprint upload component:

```css
/* globals.css additions */

/* Conflict node: animate-pulse on bg-warning/20 outer, solid bg-warning inner */
/* Use Tailwind: animate-pulse on outer div with bg-warning/20 */
@keyframes conflict-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 192, 13, 0.4); }
  50%       { box-shadow: 0 0 0 8px rgba(255, 192, 13, 0); }
}

/* Checkmark draw (conflict resolved, file processed) */
@keyframes check-draw {
  from { stroke-dashoffset: 24; }
  to   { stroke-dashoffset: 0; }
}

/* Graph edge appearing */
@keyframes edge-draw {
  from { opacity: 0; stroke-dashoffset: 100; }
  to   { opacity: 1; stroke-dashoffset: 0; }
}

/* Card entrance (Memory Inbox, feature cards) */
.card-enter {
  animation: fade-in 0.2s ease-out, slide-in-from-bottom-2 0.2s ease-out;
}

/* Card exit (conflict resolved) */
.card-exit {
  animation: fade-out 0.15s ease-in, slide-out-to-right-4 0.15s ease-in;
}
```

---

## Responsive Breakpoints

From template (Tailwind defaults, no custom breakpoints):

| Breakpoint | Width | Behavior |
|---|---|---|
| `sm` | 640px | Mobile nav hamburger |
| `md` | 768px | Two-column feature grid, mobile hook threshold |
| `lg` | 1024px | Full dashboard sidebar visible |
| `xl` | 1280px | Max content width |

**Mobile-specific rules:**
- Omnibar: `fixed bottom-0 left-0 right-0 z-50` on mobile
- Graph Explorer: renders `<ConceptList />` instead of force graph (< 768px)
- Sidebar: collapses to icon rail on tablet, drawer on mobile
- Memory Inbox cards: full-width, swipe-to-dismiss (optional enhancement)
