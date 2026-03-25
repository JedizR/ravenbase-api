# Design System — 01. Design Tokens & Brand Style Guide

> **Cross-references:** `design/00-brand-identity.md` (brand values) | `design/02-component-library.md` (components) | `design/03-screen-flows.md` (layouts)

---

## Design Philosophy

Ravenbase's visual language communicates **trusted permanence meeting intelligent precision**. The interface feels like a well-stocked academic library with shafts of light through tall windows — calm, warm, deeply navigable.

**Design personality:**
- **Warm authority** — not flashy, not cold-enterprise
- **Data-forward** — metadata labels, reference IDs, structured data
- **Premium precision** — serif elegance + mono data labels
- **Trustworthy** — nothing should feel chaotic or uncertain
- **Grounded intelligence** — approachable, organic, not tech-startup blue

> **Default mode:** Light. Dark mode is applied by adding `.dark` to `<html>`.
> No route group forces a color scheme. All pages default to light.

---

## Section 1: CSS Variables — Complete Token Reference

The BrandStyleGuide uses **Tailwind CSS v4** (`@import "tailwindcss"` + `@theme inline` block).
There is no `tailwind.config.js` — all configuration lives in `globals.css`.

```css
@custom-variant dark (&:is(.dark, .dark *));
```

### Light Mode `:root` (exact hex values — copy verbatim)

```css
:root {
  --background: #f5f3ee;
  --foreground: #1a1a1a;
  --card: #ffffff;
  --card-foreground: #1a1a1a;
  --popover: #ffffff;
  --popover-foreground: #1a1a1a;
  --primary: #2d4a3e;
  --primary-foreground: #ffffff;
  --secondary: #e8ebe6;
  --secondary-foreground: #1a1a1a;
  --muted: #e8ebe6;
  --muted-foreground: #6b7280;
  --accent: #a8c4b2;
  --accent-foreground: #1a1a1a;
  --destructive: #b53233;
  --destructive-foreground: #ffffff;
  --success: #3d8b5a;
  --success-foreground: #ffffff;
  --warning: #ffc00d;
  --warning-foreground: #1a1a1a;
  --info: #3f87c2;
  --info-foreground: #ffffff;
  --border: #d1d5db;
  --input: #d1d5db;
  --ring: #2d4a3e;
  --chart-1: #c4714a;
  --chart-2: #4fa88a;
  --chart-3: #3f7a9a;
  --chart-4: #c9a03a;
  --chart-5: #9b6eaa;
  --radius: 0.625rem;
  --sidebar: oklch(0.985 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: oklch(0.205 0 0);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.97 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.922 0 0);
  --sidebar-ring: oklch(0.708 0 0);
}
```

### Dark Mode `.dark` (exact hex values)

```css
.dark {
  --background: #1a1a1a;
  --foreground: #ededea;
  --card: #242424;
  --card-foreground: #ededea;
  --popover: #2c2c2c;
  --popover-foreground: #ededea;
  --primary: #3d6454;
  --primary-foreground: #f0f7f4;
  --secondary: #2e2e2e;
  --secondary-foreground: #ededea;
  --muted: #2e2e2e;
  --muted-foreground: #9a9a94;
  --accent: #383838;
  --accent-foreground: #ededea;
  --destructive: #e05c5c;
  --destructive-foreground: #fdf0f0;
  --success: #4fba7c;
  --success-foreground: #f0faf4;
  --warning: #ffc93d;
  --warning-foreground: #1a1200;
  --info: #5a9fd4;
  --info-foreground: #f0f6fc;
  --border: #333333;
  --input: #333333;
  --ring: #4a7a65;
  --chart-1: #d4855e;
  --chart-2: #52c493;
  --chart-3: #5599c4;
  --chart-4: #d9b84a;
  --chart-5: #b48ac2;
  --sidebar: #1a1a1a;
  --sidebar-foreground: #ededea;
  --sidebar-primary: #3d6454;
  --sidebar-primary-foreground: #f0f7f4;
  --sidebar-accent: #2e2e2e;
  --sidebar-accent-foreground: #ededea;
  --sidebar-border: #333333;
  --sidebar-ring: #4a7a65;
}
```

### `@theme inline` block (font assignments)

```css
@theme inline {
  --font-sans: "DM Sans", "Geist Fallback", sans-serif;
  --font-serif: "Playfair Display", "Georgia", serif;
  --font-mono: "JetBrains Mono", "Geist Mono", monospace;
}
```

---

## Section 2: Typography System

**Stack:**
- `font-sans` → DM Sans — all body text, UI labels, form elements
- `font-serif` → Playfair Display — hero headlines, section titles, card headers
- `font-mono` → JetBrains Mono — system labels, code, status indicators, IDs

**Type Scale (from BrandStyleGuide specimens):**

| Role | Classes | Example |
|---|---|---|
| Hero H1 | `font-serif text-5xl md:text-6xl lg:text-7xl leading-[1.1]` | "What happened, where, and when." |
| Section H2 | `font-serif text-4xl md:text-5xl leading-tight` | Feature section titles |
| Card H3 | `font-serif text-2xl` | Card and panel titles |
| Subsection H4 | `font-serif text-xl` | Sub-panel headings |
| Body Large | `font-sans text-lg` | Lead paragraphs |
| Body Default | `font-sans text-base` | General body text |
| Body Small | `font-sans text-sm` | Secondary content |
| Caption | `font-sans text-xs text-muted-foreground` | Meta, secondary labels |
| Mono Label | `font-mono text-xs tracking-wider text-muted-foreground` | `◆ MEMORY_INBOX` |
| Mono Code | `font-mono text-sm bg-secondary/50 px-2 py-1 rounded` | Inline code |
| Micro Data | `font-mono text-[10px] text-muted-foreground` | IDs, timestamps, system data |

---

## Section 3: Radius Scale

**Base radius:** `0.625rem` (≈10px — soft but not pill)

| Token | Value | Usage |
|---|---|---|
| `rounded-sm` | calc(0.625rem - 4px) ≈ 6px | Tight elements: badges, tags |
| `rounded-md` | calc(0.625rem - 2px) ≈ 8px | Buttons, inputs |
| `rounded-lg` | 0.625rem = 10px | Cards, panels |
| `rounded-xl` | calc(0.625rem + 4px) ≈ 14px | Large cards, modals |
| `rounded-2xl` | 1rem | Feature cards, sections |
| `rounded-full` | 9999px | Pills, avatars, icon buttons |

---

## Section 4: Spacing System

4px base unit (Tailwind default):

```
p-1 = 4px    p-2 = 8px    p-3 = 12px   p-4 = 16px
p-6 = 24px   p-8 = 32px   p-12 = 48px  p-16 = 64px
```

Container sizes:
```
max-w-7xl   → Primary page container (1280px)
max-w-5xl   → Pricing grid, narrow content
max-w-2xl   → Modal dialogs, forms
px-6        → Horizontal page padding (24px)
py-24       → Section vertical padding (96px)
```

Grid system:
```
Dashboard layout:   sidebar (240px fixed) + main (flex-1)
Feature cards:      grid md:grid-cols-3 gap-6
Pricing cards:      grid md:grid-cols-3 gap-6 max-w-5xl
Testimonials:       grid md:grid-cols-3 gap-6
```

---

## Section 5: Color Usage Guide

### Primary Green (`#2d4a3e` / dark: `#3d6454`)
- All CTA buttons: `bg-primary text-primary-foreground`
- Active nav items: `bg-primary text-primary-foreground`
- Sidebar background: `bg-primary` with white text
- Focus rings: `ring-ring` (maps to primary)
- Inline code accents, active selection states

### Warm Cream (`#f5f3ee`)
- Page background — the default feel is "aged paper", not white
- `bg-background` on body

### Card White (`#ffffff`)
- Surface containers on top of cream background
- `bg-card` — feels elevated vs. page background

### Forest Secondary (`#e8ebe6`)
- Subtle backgrounds, hover states, muted surfaces
- `bg-secondary` — slightly greener than neutral grey

### Sage Accent (`#a8c4b2`)
- Light green accent for badges, highlights
- `bg-accent` — NOT a hover color; use for semantic highlights

### Semantic Colors

| Token | Light | Dark | Use for |
|---|---|---|---|
| `bg-success` | `#3d8b5a` | `#4fba7c` | Resolved conflicts, completed ingestion |
| `bg-warning` | `#ffc00d` | `#ffc93d` | Pending conflicts, low credit warning |
| `bg-destructive` | `#b53233` | `#e05c5c` | Delete actions, errors |
| `bg-info` | `#3f87c2` | `#5a9fd4` | Processing states, informational |

### Warning Color Special Rule
Warning backgrounds always use `--warning-foreground` (#1a1a1a) for text — NOT white.
```css
.bg-warning, .bg-warning * {
  color: var(--warning-foreground) !important;
}
```

---

## Section 6: Ravenbase-Specific Component Patterns

### A. Conflict Card (Active)

```tsx
// Active conflict card — border-primary, primary/10 highlight for new memory
<div className="p-4 bg-card border-2 border-primary rounded-xl space-y-4">
  <div className="flex items-center justify-between">
    <span className="text-xs font-mono text-muted-foreground">MEMORY_CONFLICT</span>
    <Badge className="bg-warning text-[var(--warning-foreground)]">94% match</Badge>
  </div>
  {/* OLD memory — muted secondary */}
  <div className="flex items-start gap-3 p-3 bg-secondary/50 rounded-lg">
    <div className="w-2 h-2 rounded-full bg-muted-foreground mt-1.5 shrink-0" />
    <div>
      <p className="text-xs font-mono text-muted-foreground mb-1">OLD</p>
      <p className="text-sm">{incumbent}</p>
    </div>
  </div>
  {/* NEW memory — primary tint */}
  <div className="flex items-start gap-3 p-3 bg-primary/10 rounded-lg border border-primary/20">
    <div className="w-2 h-2 rounded-full bg-primary mt-1.5 shrink-0" />
    <div>
      <p className="text-xs font-mono text-muted-foreground mb-1">NEW</p>
      <p className="text-sm">{challenger}</p>
    </div>
  </div>
  {/* AI suggestion — accent tint */}
  <div className="p-3 bg-accent/30 rounded-lg">
    <div className="flex items-center gap-2 mb-1">
      <Sparkles className="w-3 h-3 text-primary" />
      <span className="text-xs font-mono text-muted-foreground">AI_SUGGESTION</span>
    </div>
    <p className="text-sm">{suggestion}</p>
  </div>
  {/* Action buttons */}
  <div className="flex flex-wrap gap-2">
    <Button size="sm" className="flex-1"><Check className="w-3 h-3 mr-1" />Accept New</Button>
    <Button size="sm" variant="outline" className="flex-1"><RotateCcw className="w-3 h-3 mr-1" />Keep Old</Button>
    <Button size="sm" variant="secondary"><MessageSquare className="w-3 h-3 mr-1" />Discuss</Button>
  </div>
</div>
```

### B. Memory Sticky Note

```tsx
// Warm yellow sticky note — slight rotation, amber text
<div className="bg-[#fef9c3] p-5 rounded-lg shadow-sm rotate-[-0.8deg] hover:rotate-0 transition-transform cursor-pointer">
  <p className="text-sm text-amber-950 leading-relaxed">{content}</p>
  <p className="text-[10px] text-amber-700/50 mt-4 font-mono">{date} · {profile}</p>
</div>
```

### C. Dashboard Sidebar (Forest Green)

```tsx
// Sidebar: bg-primary with white text — the primary color IS the sidebar
<div className="bg-primary text-primary-foreground rounded-xl p-4 space-y-4 w-56">
  {/* Logo */}
  <div className="flex items-center gap-2">
    {/* Sidebar collapsed: mark only */}
    <RavenbaseLogo size="sm" color="currentColor" />

    {/* Sidebar expanded: full lockup */}
    <RavenbaseLockup size="md" />
    {/* Import: import { RavenbaseLogo, RavenbaseLockup } from "@/components/brand" */}
  </div>
  {/* Profile selector */}
  <div className="flex items-center gap-2 px-2 py-1.5 bg-primary-foreground/10 border border-primary-foreground/20 rounded-lg text-xs">
    <Briefcase className="w-3 h-3 opacity-60" />
    <span className="flex-1 text-primary-foreground/80">Work Profile</span>
    <ChevronDown className="w-3 h-3 opacity-40" />
  </div>
  {/* Nav items */}
  {navItems.map(item => (
    <div className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
      item.active ? "bg-primary-foreground/20" : "hover:bg-primary-foreground/10"
    }`}>
      <item.icon className="w-4 h-4" />
      <span className="text-sm flex-1">{item.label}</span>
      {item.badge && <span className="px-1.5 py-0.5 bg-primary-foreground/20 rounded text-xs">{item.badge}</span>}
    </div>
  ))}
</div>
```

### D. File Dropzone

```tsx
<div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary transition-colors cursor-pointer">
  <Upload className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
  <h4 className="font-medium mb-2">Drop files to ingest</h4>
  <p className="text-sm text-muted-foreground mb-4">PDF, TXT, MD, JSON, ZIP (Obsidian)</p>
  <div className="flex flex-wrap gap-2 justify-center">
    <Badge variant="outline"><FileText className="w-3 h-3 mr-1" />.pdf</Badge>
    <Badge variant="outline"><FileCode className="w-3 h-3 mr-1" />.md</Badge>
    <Badge variant="outline"><FileJson className="w-3 h-3 mr-1" />.json</Badge>
    <Badge variant="outline"><FolderArchive className="w-3 h-3 mr-1" />.zip</Badge>
  </div>
</div>
```

### E. Graph Conflict Node (Pulsing Amber)

```tsx
// Unresolved conflict node — pulsing warning, NOT amber-colored circle
<div className="relative">
  <div className="w-20 h-20 rounded-full bg-warning/20 flex items-center justify-center animate-pulse">
    <div className="w-14 h-14 rounded-full bg-warning flex items-center justify-center">
      <AlertTriangle className="w-6 h-6 text-[var(--warning-foreground)]" />
    </div>
  </div>
</div>
```

### F. Section Mono Label Pattern

```tsx
// All section/feature labels — mono, small, muted, tracking-wider
<span className="text-xs font-mono text-muted-foreground tracking-wider">
  ◆ MEMORY_INBOX
</span>
// With number prefix (for section headers):
<span className="text-xs font-mono text-muted-foreground tracking-wider">
  01 — BRAND_IDENTITY
</span>
```

### G. Ingestion Queue Status

```tsx
// Status colors: complete=success, processing=info, queued=muted
{file.status === "complete" && (
  <div className="w-8 h-8 rounded bg-success/20 flex items-center justify-center">
    <CheckCircle className="w-4 h-4 text-success" />
  </div>
)}
{file.status === "processing" && (
  <div className="w-8 h-8 rounded bg-info/20 flex items-center justify-center">
    <div className="w-4 h-4 rounded-full border-2 border-info border-t-transparent animate-spin" />
  </div>
)}
{file.status === "queued" && (
  <div className="w-8 h-8 rounded bg-muted flex items-center justify-center">
    <Clock className="w-4 h-4 text-muted-foreground" />
  </div>
)}
```

### H. Toast/Notification Variants

```tsx
// Success
<div className="p-3 bg-success/10 border border-success/25 rounded-xl flex items-center gap-3">
  <CheckCircle className="w-4 h-4 text-success" />
  <p className="text-sm">Indexed 42 chunks across 3 concepts</p>
</div>
// Warning (conflict)
<div className="p-3 bg-warning/10 border border-warning/25 rounded-xl flex items-center gap-3">
  <AlertTriangle className="w-4 h-4 text-warning" />  {/* NOT text-foreground */}
  <p className="text-sm">React vs Vue: conflict detected</p>
</div>
// Error
<div className="p-3 bg-destructive/10 border border-destructive/25 rounded-xl flex items-center gap-3">
  <AlertCircle className="w-4 h-4 text-destructive" />
  <p className="text-sm">Upload failed: file exceeds 50MB limit</p>
</div>
// Info
<div className="p-3 bg-info/10 border border-info/25 rounded-xl flex items-center gap-3">
  <Info className="w-4 h-4 text-info" />
  <p className="text-sm">Graph export ready for download</p>
</div>
```

### I. Onboarding Step Indicator

```tsx
<div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-mono">
  1
</div>
```

### J. Credit / Upgrade Warning

```tsx
<div className="p-4 bg-warning/10 border border-warning/30 rounded-xl space-y-3">
  <div className="flex items-center gap-2">
    <AlertTriangle className="w-4 h-4 text-foreground" />  {/* foreground not warning on warning/10 bg */}
    <span className="text-sm font-medium text-foreground">Running low on credits</span>
  </div>
  <p className="text-xs text-muted-foreground">153 credits remaining.</p>
  <Button size="sm" className="w-full"><Zap className="w-3 h-3 mr-1" />Upgrade to Pro</Button>
</div>
```

### K. Dark Mode Toggle Button

```tsx
// Compact toggle — appears in header or settings
<button
  onClick={() => setIsDark(!isDark)}
  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary hover:bg-accent
             transition-colors text-xs font-mono text-muted-foreground border border-border"
  aria-label="Toggle dark mode"
>
  {isDark ? <Moon className="w-3.5 h-3.5 text-primary" /> : <Sun className="w-3.5 h-3.5 text-primary" />}
  <span className="hidden sm:inline">{isDark ? "Night" : "Day"}</span>
</button>
```

---

## Key Visual Decisions Summary

| Decision | Value | Notes |
|---|---|---|
| Primary color | `#2d4a3e` deep forest green | NOT navy, NOT black |
| Background | `#f5f3ee` warm cream | Like aged paper |
| Radius | `0.625rem` | ~10px, soft but not pill |
| Sidebar background | `bg-primary` (forest green) | White text on green |
| Card background | `#ffffff` | Clean white on cream |
| Warning color | `#ffc00d` | Pure amber/yellow |
| Success color | `#3d8b5a` | Forest green variant |
| Conflict node | `bg-warning animate-pulse` | Pulsing amber |
| Resolved state | `text-success` + CheckCircle | Green |
| Memory sticky notes | `bg-[#fef9c3]` + slight rotation | Yellow sticky card |
| Section mono label | `text-xs font-mono text-muted-foreground tracking-wider` | e.g. `◆ MEMORY_GRAPH` |
| CTA button | `bg-primary text-primary-foreground rounded-full` | Pill shape |

---

## Motion & Animation

```css
/* Tailwind animations */
animate-in fade-in slide-in-from-bottom-4  → Panel open
animate-out fade-out slide-out-to-bottom-4 → Panel close
animate-pulse                               → Pending conflict node (bg-warning/20 outer)
animate-spin                                → Loading spinner (border-info)
transition-colors duration-200             → Default hover transition
transition-transform duration-300          → Slide transitions

/* Memory sticky note hover — straightens on hover */
/* Applied by Tailwind: rotate-[-0.8deg] hover:rotate-0 transition-transform */

/* Conflict node: animate-pulse on bg-warning/20 outer, solid bg-warning inner */
```

Custom keyframes (add to `globals.css`):

```css
@keyframes check-draw {
  from { stroke-dashoffset: 24; }
  to   { stroke-dashoffset: 0; }
}

@keyframes edge-draw {
  from { opacity: 0; stroke-dashoffset: 100; }
  to   { opacity: 1; stroke-dashoffset: 0; }
}
```

---

## Shadcn/ui Configuration

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

### Approved shadcn/ui Components (pre-installed)

From BrandStyleGuide: `Accordion`, `AlertDialog`, `Alert`, `AspectRatio`, `Avatar`, `Badge`, `Breadcrumb`, `Button`, `ButtonGroup`, `Calendar`, `Card`, `Carousel`, `Chart`, `Checkbox`, `Collapsible`, `Command`, `ContextMenu`, `Dialog`, `Drawer`, `DropdownMenu`, `Empty`, `Field`, `Form`, `HoverCard`, `InputGroup`, `InputOTP`, `Input`, `Item`, `Kbd`, `Label`, `Menubar`, `NavigationMenu`, `Pagination`, `Popover`, `Progress`, `RadioGroup`, `Resizable`, `ScrollArea`, `Select`, `Separator`, `Sheet`, `Sidebar`, `Skeleton`, `Slider`, `Sonner`, `Spinner`, `Switch`, `Table`, `Tabs`, `Textarea`, `Toast`, `Toaster`, `ToggleGroup`, `Toggle`, `Tooltip`

**Additional packages required:**
- `cytoscape` + `cytoscape-fcose` — Graph Explorer force-directed graph
- `@tanstack/react-query` — Server state + polling
- `framer-motion` — Landing page scroll animations
- `react-dropzone` — File upload drag-and-drop

---

## Accessibility Requirements

- All interactive elements must have `aria-label` if icon-only
- Keyboard navigation required for Memory Inbox triage (J/K/Enter/Backspace)
- Color alone must never convey meaning (always add icon or text)
- Minimum contrast ratio: 4.5:1 for normal text, 3:1 for large text
- Focus ring must be visible (`ring-ring` token, `outline-hidden` → `focus-visible:ring-2`)
- Loading states must use `aria-busy` or `role="status"`
- Warning backgrounds: always pair with `text-[var(--warning-foreground)]` — never `text-white`
