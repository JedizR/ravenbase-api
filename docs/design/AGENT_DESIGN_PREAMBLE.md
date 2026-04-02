## DESIGN SYSTEM — READ BEFORE WRITING ANY JSX

Before planning or implementing any UI, read these four files in full:
1. `docs/design/00-brand-identity.md` — brand essence, voice, mono label pattern, logo spec
2. `docs/design/01-design-system.md` — all design tokens, spacing, typography scale
3. `docs/design/02-component-library.md` — domain component specs and layout patterns
4. `docs/design/04-ux-patterns.md` — interaction patterns, states, micro-animations

This is not optional. Every line of JSX must be consistent with these documents.

---

### What Ravenbase Looks Like (Non-Negotiable)

**Identity:** Warm, grounded, intelligent. Aged paper library with shafts of light.
NOT a tech startup dashboard. NOT dark-by-default. NOT blue-glowing AI aesthetic.

**Colors — use ONLY these, never override with shadcn defaults:**
- Background: `bg-background` = `#f5f3ee` (warm cream — never white, never gray-50)
- Cards: `bg-card` = `#ffffff` on the cream background
- Primary / Sidebar: `bg-primary` = `#2d4a3e` (deep forest green — never blue, never gray)
- Secondary: `bg-secondary` = `#e8ebe6`
- Accent: `bg-accent` = `#a8c4b2`
- Warning: `bg-warning` = `#ffc00d` (amber — used for conflicts, not red)
- Destructive: `bg-destructive` = `#b53233`
- Primary text on warning MUST use `text-[var(--warning-foreground)]` — never `text-white`

**Typography — never mix these up:**
- `font-sans` = DM Sans — body, UI labels, buttons
- `font-serif` = Playfair Display — hero headlines, section titles, landing h1/h2
- `font-mono` = JetBrains Mono — mono labels, system identifiers, code, ◆ labels

**Shape — these are exact, not approximate:**
- Cards: `rounded-2xl` — never `rounded-lg`, never `rounded-xl`
- Primary CTA buttons: `rounded-full` — never `rounded-md`
- Sidebar: always `bg-primary text-primary-foreground` — even in dark mode, even on mobile

**The Mono Label Pattern (Core Brand Expression):**
Every section identifier, status chip, and system label uses this pattern:
```tsx
<span className="text-xs font-mono text-muted-foreground tracking-wider">
  ◆ KNOWLEDGE_GRAPH
</span>
```
Examples: `◆ MEMORY_INBOX`, `◆ CONFLICT_QUEUE`, `◆ KNOWLEDGE_INDEX`, `◆ LIVE_PREVIEW`
Status chips: `RESOLVED`, `PENDING`, `AUTO_RESOLVED` (all caps, no ◆)
IDs: `REF-0042`, `MEM-0088`, `SRC-0007`
Never use sentence-case or title-case for these labels.

**Logo — never use a placeholder:**
- Always use `<RavenbaseLogo />` and `<RavenbaseLockup />` from `@/components/brand`
- Never use a `<div>` with "R", never use a Brain icon as a logo substitute
- Light backgrounds: `text-primary` (#2d4a3e) for both mark and wordmark
- Dark backgrounds / sidebar: `text-primary-foreground` (white)

---

### What This Product Does NOT Look Like

Reject any component that resembles these patterns:

❌ Generic hero: large gradient background + centered white text + two CTA buttons side by side
❌ Features grid: 3 or 6 cards each with a colorful icon on top and two lines of text
❌ Blue glowing orbs, network visualizations in blue, "AI brain" imagery
❌ Neon colors, glassmorphism, frosted glass nav bars
❌ Dark-by-default layout (light is the primary mode)
❌ Generic shadcn gray sidebar — the sidebar is ALWAYS forest green `bg-primary`
❌ `rounded-lg` on cards — use `rounded-2xl`
❌ `rounded-md` on primary CTAs — use `rounded-full`
❌ Gradient buttons — use solid `bg-primary` for CTAs
❌ Emojis in UI text, exclamation marks in success messages
❌ "Oops! Something went wrong 😅" — use "Upload failed: file exceeds 50MB limit"
❌ "Woohoo! Your file is ready!" — use "Indexed 42 chunks across 3 concepts"

---

### Voice Rules (Apply to All Strings)

- Precise over flowery: "Your knowledge graph has 247 nodes" not "Your amazing network is growing!"
- Active over passive: "Detected a conflict" not "A conflict was detected"
- Direct over hedged: "This conflicts with what you said in 2022" not "This may potentially conflict"
- Never: "leverage", "utilize", "synergy", "amazing", "awesome"
- Empty states: "Upload your first file to start building your knowledge graph" — not motivational fluff

---

### Animation — Use Only These Patterns

- Card entrance: `animate-in fade-in slide-in-from-bottom-2 duration-200`
- Card exit: `animate-out fade-out slide-out-to-right-4 duration-150`
- Conflict node pulse: `animate-pulse` on `bg-warning/20` outer ring
- Resolved state: checkmark draw animation (`check-draw` keyframe from globals.css)
- Hover on interactive cards: `hover:shadow-md transition-shadow duration-150`
- No bouncing, no elastic springs, no dramatic scale effects

---

### Checklist Before Committing Any UI

□ Did I use `bg-background` (#f5f3ee) not white/gray as the page background?
□ Did I use `rounded-2xl` on all cards?
□ Did I use `rounded-full` on all primary CTA buttons?
□ Did I use `font-serif` Playfair Display on all hero/section headlines?
□ Did I use the `◆ SNAKE_CASE` mono label pattern for all section identifiers?
□ Is the sidebar `bg-primary` (forest green) — not gray, not dark?
□ Did I use amber `#ffc00d` for warnings — not red, not orange?
□ Are all logo usages via `<RavenbaseLogo />` or `<RavenbaseLockup />`?
□ Does this look like a warm library tool — not a tech startup dashboard?
