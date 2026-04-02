# STORY-038 — Final UX Polish Pass

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P0 (must complete before launch)
**Complexity:** Large
**Sprint:** 38
**Depends on:** All stories STORY-031 through STORY-037 complete

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfies? -->
None — final UX polish and production hardening story.

## Component
All Components — cross-cutting audit

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` (all 19 frontend rules — read every rule carefully)
> 2. `docs/design/AGENT_DESIGN_PREAMBLE.md` — NON-NEGOTIABLE visual rules, anti-patterns, and pre-commit checklist. Read fully before writing any JSX. This is the single most important design file.
> 3. `docs/design/00-brand-identity.md` — brand colors, mono labels, voice rules, logo spec
> 4. `docs/design/01-design-system.md` — all color tokens, typography, component specs
> 5. `docs/design/02-component-library.md` — component anatomy and usage
> 6. `docs/design/04-ux-patterns.md` — interaction patterns, animations, micro-interactions
> 7. `docs/stories/epics.md` — confirm all 37 previous stories are marked ✅ before starting
> 8. `docs/.bmad/project-status.md` — confirm current sprint is 38

---

## User Story

As a pre-launch quality engineer, I want to perform a complete end-to-end audit of the
entire Ravenbase frontend so that every page feels polished, every interaction has
feedback, and every color matches the brand system — before real users see it.

---

## Context

STORY-038 is the final gate in Phase B (Frontend). All 37 preceding stories have been
implemented across 8 epics covering foundation, ingestion, knowledge graph, conflict
detection, meta-document generation, auth, marketing, and polish.

After 37 stories of implementation, visual drift accumulates:
- Hardcoded hex colors slip through code reviews
- Typography classes get applied inconsistently
- Animation timings diverge from spec
- Brand colors used in wrong contexts
- Pages built in isolation miss cross-page consistency
- Loading states are missing on async routes

This story corrects all of that in a single systematic pass.

**What this story IS:**
- A **quality audit and surface correction pass**
- Verifying that what was built matches the design system specification exactly
- Fixing violations found during the audit

**What this story IS NOT:**
- NOT a feature story — no new functionality is built
- NOT a bug fix story — it doesn't address specific bug reports
- NOT a performance optimization story — it doesn't refactor for speed
- NOT adding new pages — all pages already exist from previous stories

---

## Acceptance Criteria

### AC-1: Brand Color Audit (0 hardcoded hex defects)
- [ ] AC-1a: Sidebar: `bg-primary` (#2d4a3e) in BOTH light and dark mode — never `bg-background`, never `bg-sidebar`
- [ ] AC-1b: Page background: `bg-background` (#f5f3ee light, #1a1a1a dark)
- [ ] AC-1c: All CTA buttons: `bg-primary rounded-full` — no `rounded-md` or `rounded-lg` on primary CTAs
- [ ] AC-1d: All cards: `bg-card rounded-2xl border border-border` — no `rounded-xl`, no `rounded-lg`
- [ ] AC-1e: Active nav items: `bg-primary-foreground/15 text-primary-foreground`
- [ ] AC-1f: Progress bars: `[&>div]:bg-primary` — forest green fill
- [ ] AC-1g: Focus rings: `ring-2 ring-primary/30` — forest green focus
- [ ] AC-1h: Conflict/warning badges: `bg-warning text-[var(--warning-foreground)]` — amber with dark text
- [ ] AC-1i: No hardcoded hex colors in any component file (`#2d4a3e`, `#f5f3ee`, `#e8ebe6`, `#a8c4b2`, `#ffc00d`)

**Verification method:** `grep -rn "#2d4a3e\|#f5f3ee\|#e8ebe6\|#ffc00d\|#a8c4b2\|#1a1a1a" components/ app/ --include="*.tsx" --include="*.ts"` — every match must be inside a CSS variable definition or a comment, never in a Tailwind className string.

### AC-2: Typography Audit (0 font-family defects)
- [ ] AC-2a: All page H1 headlines: `font-serif` (Playfair Display) — not `font-sans`
- [ ] AC-2b: All section H2 headlines: `font-serif`
- [ ] AC-2c: All body text: `font-sans` (DM Sans)
- [ ] AC-2d: All mono labels (◆ LABEL_NAME): `font-mono` (JetBrains Mono) — never `font-sans`
- [ ] AC-2e: All status chips and system identifiers: `font-mono`
- [ ] AC-2f: All code blocks: `font-mono`

### AC-3: Shape & Border Radius Audit (0 shape defects)
- [ ] AC-3a: All cards: `rounded-2xl` — never `rounded-lg`, never `rounded-xl`
- [ ] AC-3b: All primary CTA buttons: `rounded-full` — never `rounded-md`
- [ ] AC-3c: All dialog/modal content: `rounded-2xl`
- [ ] AC-3d: All input fields: `rounded-xl`

### AC-4: Micro-Interaction Audit (0 missing interactions)
Each item must be manually verified in browser at 1440px desktop:
- [ ] AC-4a: Primary buttons: `hover:-translate-y-px active:translate-y-0` lift on hover, press down on click
- [ ] AC-4b: Secondary buttons: `hover:bg-secondary` background color shift on hover
- [ ] AC-4c: Cards: `hover:shadow-md transition-shadow` shadow increase on hover
- [ ] AC-4d: Nav links in marketing header: underline grows from left on hover
- [ ] AC-4e: Sidebar nav items: `hover:scale-110` icon scale on hover
- [ ] AC-4f: Inputs: `focus:ring-2 focus:ring-primary/30 focus:border-primary` forest green ring + border on focus
- [ ] AC-4g: Dropdown menus: `animate-in fade-in zoom-in-95` scale+fade on open
- [ ] AC-4h: Sonner toasts: toast-swap animation (built into sonner)
- [ ] AC-4i: Conflict cards: slide-out-right animation on resolve (tw-animate-css)
- [ ] AC-4j: Progress bars: `transition-all duration-300 ease-out` width transition

### AC-5: Page-by-Page Functional Audit

**/login:**
- [ ] AC-5a: Clerk SignIn renders with Ravenbase brand lockup above
- [ ] AC-5b: Background is warm cream `bg-background` (#f5f3ee)
- [ ] AC-5c: After login redirects to `/chat`

**/register:**
- [ ] AC-5d: Clerk SignUp renders with Ravenbase brand lockup above
- [ ] AC-5e: Background is warm cream `bg-background`
- [ ] AC-5f: After register redirects to `/onboarding`

**/onboarding:**
- [ ] AC-5g: Step indicator shows "Step X of 3" with time estimate
- [ ] AC-5h: Role cards: `hover:-translate-y-1 hover:shadow-md` lift on hover
- [ ] AC-5i: "Nice to meet you, [Name]!" appears after name entry
- [ ] AC-5j: Step 3 progress bar: `bg-primary` forest green fill
- [ ] AC-5k: Confetti animation on completion
- [ ] AC-5l: Redirects to `/chat?first_run=true` after completion

**/chat:**
- [ ] AC-5m: Empty state shows example prompt chips
- [ ] AC-5n: User messages: `bg-secondary rounded-2xl` right-aligned
- [ ] AC-5o: Assistant messages: `bg-card border border-border rounded-2xl` left-aligned
- [ ] AC-5p: Typing indicator (3 bouncing dots) while streaming
- [ ] AC-5q: Citations render as clickable `font-mono` cards below message
- [ ] AC-5r: Session list in sidebar updates after each conversation
- [ ] AC-5s: Input: Enter sends, Shift+Enter inserts newline

**/graph:**
- [ ] AC-5t: Cytoscape renders with forest green nodes
- [ ] AC-5u: Clicking a node opens GraphNodePanel Sheet from right
- [ ] AC-5v: Filter bar: `bg-card rounded-2xl` container
- [ ] AC-5w: NL query bar appears above filter bar
- [ ] AC-5x: Query results highlight nodes in amber `bg-warning`
- [ ] AC-5y: Mobile: ConceptList renders instead of Cytoscape

**/workstation:**
- [ ] AC-5z: Prompt textarea expands on focus
- [ ] AC-5aa: Generate button: `bg-primary rounded-full`
- [ ] AC-5ab: Streaming output: blinking `▌` cursor
- [ ] AC-5ac: Auto-save indicator: `◆ SAVED_JUST_NOW` mono label after generation
- [ ] AC-5ad: Export MD and Export PDF buttons work
- [ ] AC-5ae: History sidebar lists previous documents
- [ ] AC-5af: Mobile: history in Sheet drawer

**/sources:**
- [ ] AC-5ag: Upload Files tab: IngestionDropzone is functional
- [ ] AC-5ah: Dropzone: dashed border, changes on drag-over
- [ ] AC-5ai: Import from AI Chat tab: prompt loads, copy button works
- [ ] AC-5aj: Import submit shows IngestionProgress SSE bar

**/inbox:**
- [ ] AC-5ak: Conflict cards render with OLD/NEW rows
- [ ] AC-5al: J/K navigates between cards
- [ ] AC-5am: Enter accepts, Backspace rejects
- [ ] AC-5an: C opens ConflictChat
- [ ] AC-5ao: ? shows ShortcutOverlay
- [ ] AC-5ap: Cards animate in on load, slide out on resolve
- [ ] AC-5aq: Empty state shows animated checkmark

**/settings:**
- [ ] AC-5ar: AI model cards: selected state has `border-2 border-primary`
- [ ] AC-5as: Notification toggles: `bg-primary` when on
- [ ] AC-5at: Profile CRUD: create/edit/delete all work

**/settings/billing:**
- [ ] AC-5au: Shows current tier
- [ ] AC-5av: Pro/Team: "Manage subscription" opens Stripe portal
- [ ] AC-5aw: Free: "Upgrade to Pro" links to `/#pricing`

**/settings/referrals:**
- [ ] AC-5ax: Referral link displays correctly
- [ ] AC-5ay: Copy button shows 2s "COPIED!" state
- [ ] AC-5az: Stats card shows referral count

**/settings/data:**
- [ ] AC-5ba: Format selector shows 3 options
- [ ] AC-5bb: Export button triggers download
- [ ] AC-5bc: Delete account opens AlertDialog with "DELETE" confirmation input

**/ (landing page):**
- [ ] AC-5bd: All 9 sections render
- [ ] AC-5be: Pricing section accessible via /#pricing anchor
- [ ] AC-5bf: Scroll animations play on features section
- [ ] AC-5bg: Header nav links scroll to correct sections
- [ ] AC-5bh: CTA buttons link to `/register`
- [ ] AC-5bi: Footer Privacy + Terms links work

**/privacy and /terms:**
- [ ] AC-5bj: Both pages render with Header + Footer
- [ ] AC-5bk: No 404 errors

### AC-6: Accessibility Audit (WCAG 2.1 AA — 0 critical violations)
- [ ] AC-6a: Every page has skip-to-content link as first focusable element
- [ ] AC-6b: All images have alt text
- [ ] AC-6c: All interactive elements reachable via Tab key
- [ ] AC-6d: No keyboard traps
- [ ] AC-6e: aria-live regions on all streaming content
- [ ] AC-6f: `npx axe-cli http://localhost:3000 --tags wcag2a,wcag2aa` → 0 critical violations
- [ ] AC-6g: `npx axe-cli http://localhost:3000/onboarding --tags wcag2a,wcag2aa` → 0 critical violations
- [ ] AC-6h: `npx axe-cli http://localhost:3000/graph --tags wcag2a,wcag2aa` → 0 critical violations

### AC-7: Performance Audit
- [ ] AC-7a: `npm run build` passes: 0 TypeScript errors, 0 warnings
- [ ] AC-7b: `npm run test` passes: 0 test failures
- [ ] AC-7c: No `console.error` or `console.warn` in production code
- [ ] AC-7d: All heavy imports use dynamic import (cytoscape, react-markdown)
- [ ] AC-7e: All async dashboard routes have `loading.tsx` sibling files

### AC-8: Mobile Audit (test at 375px viewport)
- [ ] AC-8a: All touch targets ≥ 44px height
- [ ] AC-8b: No horizontal overflow on any page
- [ ] AC-8c: Sidebar renders as Sheet drawer
- [ ] AC-8d: Mobile menu opens and closes correctly
- [ ] AC-8e: Input keyboards don't cause layout shift
- [ ] AC-8f: Pricing cards stack vertically

---

## Technical Notes

### Development Sequence

**Phase 1: Global CSS and Brand Foundation (do FIRST)**
1. Run hardcoded hex audit — document every match
2. Fix all hardcoded hex colors — replace with CSS variable equivalents
3. Verify `app/globals.css` has complete `:root` and `.dark` token sets
4. Run `npm run build` — confirm 0 TypeScript errors

**Phase 2: Page-by-Page Audit (following AC-5 order)**
Visit each page in order. Document failures. Fix in priority order:
- Broken functionality (buttons that don't work, broken links) — highest priority
- Visual drift (wrong colors, fonts, shapes) — medium priority
- Missing micro-interactions — lower priority

**Phase 3: Accessibility Sweep**
Run axe-cli on all 3 key pages. Fix critical violations first.

**Phase 4: Mobile Sweep**
Test at 375px. Fix overflow and touch target issues.

**Phase 5: Final Build Verification**
`npm run build && npm run test` — must both pass with 0 failures.

### Hardcoded Hex Audit — Exact Replace Map

If you find hardcoded hex values, replace with the correct CSS variable:

| Hardcoded Value | Replace With | Context |
|---|---|---|
| `#2d4a3e` | `bg-primary` | Forest green CTAs, sidebar |
| `#f5f3ee` | `bg-background` | Page background |
| `#e8ebe6` | `bg-secondary` | Hover surfaces |
| `#a8c4b2` | `bg-accent` | Accent highlights |
| `#ffc00d` | `bg-warning` | Conflict/warning badges |
| `#1a1a1a` | `text-foreground` or `bg-foreground` | Dark text |
| `#ffffff` | `bg-card` | Card backgrounds |
| `#333333` | `var(--border)` in dark mode | Dark borders |
| `#6b7280` | `text-muted-foreground` | Muted text |

---

## Definition of Done

- [ ] `npm run build`: 0 TypeScript errors, 0 warnings
- [ ] `npm run test`: 0 test failures
- [ ] All AC-1 (brand color) items checked — 0 hardcoded hex violations
- [ ] All AC-2 (typography) items checked — 0 font-family violations
- [ ] All AC-3 (shape) items checked — 0 border-radius violations
- [ ] All AC-4 (micro-interactions) verified in browser — 0 missing
- [ ] All AC-5 (page-by-page) items checked — 0 functional defects
- [ ] All AC-6 (accessibility) items checked — 0 critical axe violations
- [ ] All AC-7 (performance) items checked
- [ ] All AC-8 (mobile) items checked
- [ ] Product walked through by a real person from /register → onboarding → chat → graph → workstation → sources → inbox
- [ ] Zero pages return 404 when navigated to from within the app
- [ ] No unhandled JavaScript errors in browser console on any page

---

## Final Localhost Verification (mandatory before marking complete)

After `npm run build` and `npm run test` both pass, verify the running application:

**Step 1 — Clear stale cache:**
```bash
rm -rf .next
```

**Step 2 — Start dev server:**
```bash
npm run dev
```

**Step 3 — Full page audit (visit in order):**
- [ ] http://localhost:3000/register
- [ ] http://localhost:3000/login
- [ ] http://localhost:3000/onboarding
- [ ] http://localhost:3000/chat
- [ ] http://localhost:3000/graph
- [ ] http://localhost:3000/workstation
- [ ] http://localhost:3000/sources
- [ ] http://localhost:3000/inbox
- [ ] http://localhost:3000/settings
- [ ] http://localhost:3000/settings/billing
- [ ] http://localhost:3000/settings/referrals
- [ ] http://localhost:3000/settings/data
- [ ] http://localhost:3000/
- [ ] http://localhost:3000/privacy
- [ ] http://localhost:3000/terms

**Step 4 — Browser DevTools Console (on each page):**
Confirm no red errors on any page. Yellow warnings acceptable.

**Step 5 — Mobile test (DevTools → Toggle Device Toolbar → iPhone 12):**
- [ ] Sidebar becomes Sheet drawer
- [ ] No horizontal overflow
- [ ] All touch targets ≥ 44px

**Step 6 — Report one of:**
- ✅ `localhost verified` — all pages render correctly
- ⚠️ `Issue found: [page + describe issue]` — fix before committing docs

Only commit the docs update after ALL pages pass localhost verification.

---

## Testing This Story

```bash
# Build check:
npm run build
npm run test

# Hardcoded hex audit (0 matches in component files):
grep -rn "#2d4a3e\|#f5f3ee\|#e8ebe6\|#ffc00d\|#a8c4b2" \
  components/ app/ --include="*.tsx" --include="*.ts" \
  | grep -v "\.css:" | grep -v "// " | grep -v "cssVariable"

# Typography audit (0 H1/H2 without font-serif):
grep -rn "text-4xl\|text-5xl\|text-3xl" app/ components/ \
  --include="*.tsx" | grep -v "font-serif"

# Missing loading.tsx audit (0 missing):
find app/\(dashboard\) -name "page.tsx" | while read p; do
  dir=$(dirname "$p")
  [ -f "$dir/loading.tsx" ] || echo "MISSING: $dir/loading.tsx"
done

# Accessibility check (0 critical):
npx axe-cli http://localhost:3000 --tags wcag2a,wcag2aa
npx axe-cli http://localhost:3000/onboarding --tags wcag2a,wcag2aa
npx axe-cli http://localhost:3000/graph --tags wcag2a,wcag2aa
```

---

## Frontend Agent Brief

> **Skill Invocations — paste each skill call before starting that phase:**
>
> **Phase 1 (Read/Design):** `Use /frontend-design — enforce production-grade aesthetic compliance`
> **Phase 2 (CSS/Tokens):** `Use /tailwindcss — for Tailwind CSS v4 token system`
> **Phase 3 (Layout):** `Use /tailwindcss-advanced-layouts — for multi-page layout audit`
> **Phase 4 (Accessibility):** `Use /tailwindcss-animations — for micro-interaction verification`
> **Phase 5 (Mobile):** `Use /tailwindcss-mobile-first — for responsive/mobile verification`
> **Phase 6 (Final verification):** `Use /superpowers:verification-before-completion — before claiming done`

---

```
🎯 Target: Claude Code / MiniMax-M2.7 — Ultra-detailed audit implementation prompt
💡 Optimized for: MiniMax-M2.7 — exact commands, exact output, exact fix map
📋 Nature: QUALITY AUDIT + SURFACE CORRECTION PASS — not implementation

═══════════════════════════════════════════════════════════════════
NATURE OF THIS STORY
═══════════════════════════════════════════════════════════════════

This is a QUALITY AUDIT AND SURFACE CORRECTION PASS.

What you ARE doing:
- Running EVERY command exactly as specified
- Recording EXACT output for each command
- Fixing violations using the EXACT replace map provided
- Creating an audit results document (STORY-038-AUDIT.md)

What you are NOT doing:
- NOT building new features
- NOT changing business logic
- NOT refactoring components for performance (only fix what the audit finds)

═══════════════════════════════════════════════════════════════════
READING ORDER (mandatory — read ALL before touching code)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /frontend-design

Read ALL files in this order. Write "✅ CONFIRMED READ: [filename]" after each:

1. CLAUDE.md — all 19 rules. Study especially:
   - RULE 5: no forced color mode in route groups
   - RULE 10: every dashboard page must have loading.tsx
   - RULE 15: metadata on marketing pages, noindex on dashboard
   - RULE 16: skip link on every page
   - RULE 18: blur-debounce validation pattern

2. docs/design/AGENT_DESIGN_PREAMBLE.md — entire file, every anti-pattern
   → Automatic rejection list (never ask before fixing):
     ❌ Hardcoded hex in JSX
     ❌ Rounded-lg on cards
     ❌ Rounded-md on CTAs
     ❌ font-sans on h1/h2
     ❌ ◆ label without font-mono
     ❌ Page without loading.tsx

3. docs/design/00-brand-identity.md — exact hex values, mono label pattern ◆

4. docs/design/01-design-system.md — all 18 CSS variables :root and .dark
   → Read the entire file. You must know the EXACT hex values.

5. docs/design/04-ux-patterns.md — micro-interaction specs, animation timings
   → Read the entire file. You must know exact animation durations.

6. docs/stories/epics.md — confirm all 37 previous stories listed as ✅

7. docs/stories/EPIC-08-polish/STORY-038.md (this file)
   → All 8 AC categories. Study each verification command.

CONFIRMED READ: All 7 files read.

═══════════════════════════════════════════════════════════════════
PHASE 1 — HARDCODE HEX AUDIT (AC-1i)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss

Run this EXACT command and record EVERY match:

```bash
grep -rn "#2d4a3e\|#f5f3ee\|#e8ebe6\|#ffc00d\|#a8c4b2\|#1a1a1a\|#ffffff\|#333333\|#6b7280" \
  components/ app/ --include="*.tsx" --include="*.ts" \
  | grep -v "\.css:" \
  | grep -v "//.*#" \
  | grep -v "cssVariable" \
  | grep -v "PLACEHOLDER" \
  | sort
```

For each match, record:
- File path + line number
- The actual line content
- VIOLATION (in component file) or OK (in globals.css comment)

If ANY violations found in component files → fix immediately using this map:

| Hex Found | Replace With | Conditions |
|---|---|---|
| `#2d4a3e` | `bg-primary` | In className |
| `#2d4a3e` | `text-primary` | In className (text color) |
| `#f5f3ee` | `bg-background` | In className |
| `#e8ebe6` | `bg-secondary` | In className |
| `#a8c4b2` | `bg-accent` | In className |
| `#ffc00d` | `bg-warning` | In className |
| `#1a1a1a` | `text-foreground` | In className (text color) |
| `#1a1a1a` | `bg-foreground` | In className (bg color) |
| `#ffffff` | `bg-card` | In className |
| `#333333` | `border-border` | In className (dark mode border) |
| `#6b7280` | `text-muted-foreground` | In className |

Verify fix: re-run the grep. Expected: 0 violations in component files.

═══════════════════════════════════════════════════════════════════
PHASE 2 — CSS VARIABLES VERIFICATION (prerequisite for all ACs)
═══════════════════════════════════════════════════════════════════

Open app/globals.css. READ IT COMPLETELY.

Confirm ALL of these exist in :root (exact values required):
--background: #f5f3ee        ✅ / ❌
--foreground: #1a1a1a         ✅ / ❌
--primary: #2d4a3e            ✅ / ❌
--primary-foreground: #ffffff  ✅ / ❌
--secondary: #e8ebe6          ✅ / ❌
--muted-foreground: #6b7280   ✅ / ❌
--accent: #a8c4b2              ✅ / ❌
--warning: #ffc00d             ✅ / ❌
--warning-foreground: #78350f  ✅ / ❌
--border: #d1d5db              ✅ / ❌
--card: #ffffff                ✅ / ❌
--card-foreground: #1a1a1a    ✅ / ❌
--radius: 1rem                 ✅ / ❌ (= rounded-2xl in Tailwind)

Confirm ALL of these exist in .dark:
--background: #1a1a1a          ✅ / ❌
--foreground: #ededea          ✅ / ❌
--primary: #3d6454             ✅ / ❌
--primary-foreground: #f0f7f4  ✅ / ❌
--secondary: #2e2e2e           ✅ / ❌
--muted-foreground: #9a9a94   ✅ / ❌
--border: #333333              ✅ / ❌
--card: #242424                ✅ / ❌

IF ANY MISSING OR WRONG → fix globals.css FIRST before any other work.

Confirm @theme inline maps fonts:
@theme inline {
  --font-sans: var(--font-dm-sans), "DM Sans", sans-serif;
  --font-serif: var(--font-playfair-display), "Playfair Display", Georgia, serif;
  --font-mono: var(--font-jetbrains-mono), "JetBrains Mono", monospace;
}
Expected: all three font variables defined

═══════════════════════════════════════════════════════════════════
PHASE 3 — AC-1 BRAND COLOR AUDIT (run ALL sub-commands)
═══════════════════════════════════════════════════════════════════

AC-1a: Sidebar uses bg-primary in both light and dark mode
Command:
  grep -rn "bg-primary" app/\(dashboard\)/layout.tsx components/domain/Sidebar.tsx 2>/dev/null | head -10
Expected: className contains "bg-primary" on sidebar container
FAIL → document file:line and fix

AC-1b: Page backgrounds use bg-background (not bg-white)
Command:
  grep -rn "bg-white\|bg-background" app/\(dashboard\)/ --include="*.tsx" | head -10
Expected: bg-background used, no bg-white in component classNames
FAIL → document and fix

AC-1c: CTA buttons use rounded-full (not rounded-md)
Command:
  grep -rn "bg-primary rounded-md\|bg-primary rounded-lg\|bg-primary rounded-xl" components/ app/ --include="*.tsx"
Expected: 0 matches — all primary CTAs must be rounded-full
FAIL → document each violation

AC-1d: All cards use rounded-2xl (not rounded-lg, not rounded-xl)
Command:
  grep -rn "bg-card rounded-lg\|bg-card rounded-xl\|bg-card rounded-md" components/ app/ --include="*.tsx"
Expected: 0 matches — all cards must be rounded-2xl
FAIL → document each violation

AC-1e: Active nav items use bg-primary-foreground/15
Command:
  grep -rn "bg-primary-foreground/15\|bg-primary-foreground/10" components/ --include="*.tsx" | head -5
Expected: active nav items have this class
FAIL → document and fix

AC-1f: Progress bars use bg-primary fill
Command:
  grep -rn "\[&>div\]:bg-primary\|bg-primary.*rounded-full.*h-\|Progress.*bg-primary" components/ --include="*.tsx" | head -5
Expected: progress bar fills use bg-primary
FAIL → document and fix

AC-1g: Focus rings use ring-primary/30
Command:
  grep -rn "focus:ring-primary/30\|focus-visible:ring-primary/30\|ring-primary/30" components/ --include="*.tsx" | head -5
Expected: focus states use forest green ring
FAIL → document and fix

AC-1h: Conflict/warning badges use bg-warning text-[var(--warning-foreground)]
Command:
  grep -rn "bg-warning\|text-warning-foreground" components/domain/ --include="*.tsx" | grep -v "text-muted" | head -10
Expected: conflict/warning badges use bg-warning
FAIL → document and fix

AC-1i: Zero hardcoded hex in component files (already done in Phase 1)

AC-1 SUMMARY: Record PASS/FAIL for each sub-item. Fix all FAILs before proceeding.

═══════════════════════════════════════════════════════════════════
PHASE 4 — AC-2 TYPOGRAPHY AUDIT (run ALL sub-commands)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss

AC-2a: All H1 use font-serif (not font-sans)
Command:
  grep -rn "text-[0-9]xl" app/\(marketing\)/ --include="*.tsx" | grep -v "font-serif" | head -20
Expected: 0 matches — all H1 must have font-serif
FAIL → document each violation

AC-2b: All H2 use font-serif
Command:
  grep -rn "text-2xl\|text-3xl" components/ app/ --include="*.tsx" | grep -v "font-serif" | head -20
Expected: 0 matches — all H2 must have font-serif
FAIL → document each violation

AC-2c: All body text uses font-sans (default — no class needed, verify no font-serif on body)
Command:
  grep -rn "className.*font-serif.*text-base\|className.*font-serif.*text-sm" components/ app/ --include="*.tsx" | head -5
Expected: body text does not use font-serif
FAIL → document and fix

AC-2d: All ◆ mono labels use font-mono (not font-sans)
Command:
  grep -rn "◆ " components/ app/ --include="*.tsx" | grep -v "font-mono" | head -20
Expected: 0 matches — all ◆ labels must be font-mono
FAIL → document each violation

AC-2e: All status chips use font-mono
Command:
  grep -rn "rounded-full.*text-xs\|rounded-full.*text-sm" components/ --include="*.tsx" | grep -v "font-mono" | head -10
Expected: status chips have font-mono
FAIL → document and fix

AC-2f: All code blocks use font-mono
Command:
  grep -rn "bg-secondary.*font-mono\|font-mono.*bg-secondary" components/ --include="*.tsx" | head -5
Expected: code blocks use font-mono
FAIL → document and fix

AC-2 SUMMARY: Record PASS/FAIL for each sub-item. Fix all FAILs before proceeding.

═══════════════════════════════════════════════════════════════════
PHASE 5 — AC-3 SHAPE/BORDER RADIUS AUDIT (run ALL sub-commands)
═══════════════════════════════════════════════════════════════════

AC-3a: All cards use rounded-2xl (not rounded-lg, not rounded-xl)
Command:
  grep -rn "bg-card rounded-lg\|bg-card rounded-xl\|bg-card rounded-md" components/ app/ --include="*.tsx"
Expected: 0 matches
FAIL → document each violation

AC-3b: All primary CTAs use rounded-full (not rounded-md, not rounded-lg)
Command:
  grep -rn "bg-primary rounded-md\|bg-primary rounded-lg\|bg-primary rounded-xl" components/ app/ --include="*.tsx"
Expected: 0 matches
FAIL → document each violation

AC-3c: All dialog/modal content uses rounded-2xl
Command:
  grep -rn "DialogContent\|AlertDialogContent" components/ --include="*.tsx" | head -5
Expected: shadcn Dialog content is rounded-2xl by default (verify)
FAIL → document

AC-3d: All inputs use rounded-xl (not rounded-lg, not rounded-md on border)
Command:
  grep -rn "border.*rounded-lg\|border.*rounded-md" components/ --include="*.tsx" | head -10
Expected: input fields should be rounded-xl
FAIL → document each violation

AC-3 SUMMARY: Record PASS/FAIL for each sub-item. Fix all FAILs before proceeding.

═══════════════════════════════════════════════════════════════════
PHASE 6 — AC-4 MICRO-INTERACTIONS AUDIT (manual verification)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-animations

These items must be VERIFIED IN BROWSER at 1440px desktop. grep alone is insufficient.

For each item: open the component, verify the className contains the required pattern.

AC-4a: Primary buttons: hover:-translate-y-px active:translate-y-0
  grep -rn "hover:-translate-y-px" components/ --include="*.tsx" | head -5
  Verify: Button component has both hover and active classes

AC-4b: Secondary buttons: hover:bg-secondary
  grep -rn "hover:bg-secondary" components/ --include="*.tsx" | head -5
  Verify: Button variant="secondary" or outline has this hover

AC-4c: Cards: hover:shadow-md transition-shadow
  grep -rn "hover:shadow-md" components/ --include="*.tsx" | head -5
  Verify: interactive cards have shadow lift on hover

AC-4d: Marketing nav links: underline grow animation (NOT bg-primary hover)
  grep -rn "hover:bg-primary" components/marketing/Header.tsx | head -5
  Expected: nav links do NOT use bg-primary hover
  Verify: nav links use underline animation instead

AC-4e: Sidebar nav items: hover:scale-110
  grep -rn "hover:scale-110" components/domain/Sidebar.tsx 2>/dev/null | head -5
  Verify: sidebar icons scale on hover

AC-4f: Inputs: focus:ring-2 focus:ring-primary/30 focus:border-primary
  grep -rn "focus:ring-primary/30" components/ --include="*.tsx" | head -5
  Verify: form inputs have forest green focus ring

AC-4g: Dropdown menus: animate-in fade-in zoom-in-95
  grep -rn "animate-in fade-in zoom-in-95" components/ --include="*.tsx" | head -5
  Verify: dropdowns have scale+fade animation

AC-4h: Sonner toasts: built into sonner (verify sonner is imported)
  grep -rn "import.*Sonner\|import.*toast" components/ --include="*.tsx" | head -5
  Verify: SonnerToaster is present in root layout

AC-4i: Conflict cards: slide-out-right animation on resolve
  grep -rn "animate-out.*slide-out\|slide-out-right" components/ --include="*.tsx" | head -5
  Verify: conflict cards have exit animation

AC-4j: Progress bars: transition-all duration-300 ease-out
  grep -rn "duration-300.*transition\|transition.*duration-300" components/ --include="*.tsx" | head -5
  Verify: progress bar width transitions smoothly

AC-4 SUMMARY: Record PASS/FAIL for each. For any FAIL, add the missing class.

═══════════════════════════════════════════════════════════════════
PHASE 7 — AC-5 PAGE-BY-PAGE AUDIT (run npm build first)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-advanced-layouts

Start dev server: npm run dev

For EACH page below, visit and verify:

Pages to audit (in this exact order):
1. /register — Clerk renders, brand lockup, cream background
2. /login — Clerk renders, brand lockup, cream background
3. /onboarding — Step indicator, role cards, confetti
4. /chat — Empty state chips, message rendering, streaming
5. /graph — Cytoscape renders, node panel, filter bar
6. /workstation — Prompt textarea, generate button, streaming output
7. /sources — Dropzone functional, progress bar
8. /inbox — Conflict cards, keyboard nav
9. /settings — Model cards, toggles
10. /settings/billing — Tier display, Stripe portal
11. /settings/referrals — Copy button, stats
12. /settings/data — Export, delete account
13. / — All 9 sections, pricing anchor, footer
14. /privacy — Header + Footer + content + skip link
15. /terms — Header + Footer + content + skip link

For each page, record this exact format:

[PASS/FAIL] URL
- Brand colors: OK / LIST ISSUES
- Typography: OK / LIST ISSUES
- Shapes: OK / LIST ISSUES
- Required elements: OK / LIST MISSING
- Notes: [specific observations]

═══════════════════════════════════════════════════════════════════
PHASE 8 — AC-6 ACCESSIBILITY AUDIT (run axe on 3 key pages)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /superpowers:verification-before-completion

Ensure dev server is running: npm run dev

Run these EXACT commands:

```bash
npx axe-cli http://localhost:3000 --tags wcag2a,wcag2aa
npx axe-cli http://localhost:3000/onboarding --tags wcag2a,wcag2aa
npx axe-cli http://localhost:3000/graph --tags wcag2a,wcag2aa
```

For each, record:
- Command output
- Number of critical violations (must be 0)
- Number of serious violations (target: 0, document if > 0)
- Number of moderate violations (target: 0, document if > 0)

Manual checks (run in browser):
□ Every page has skip link as first focusable element
□ Every page has <main id="main-content">
□ No keyboard traps
□ All images have alt text
□ aria-live regions on streaming content (chat, workstation)

═══════════════════════════════════════════════════════════════════
PHASE 9 — AC-7 PERFORMANCE AUDIT (run ALL commands)
═══════════════════════════════════════════════════════════════════

npm run build
Expected: 0 TypeScript errors, 0 warnings
Actual: ____ errors, ____ warnings

npm run test
Expected: 0 failures
Actual: ____ failures

No console.error/warn in production code:
grep -rn "console.error\|console.warn" components/ app/ --include="*.tsx" --include="*.ts" | grep -v "logger\|log\."
Expected: 0 matches
Actual: ____ matches

Missing loading.tsx files:
find app/\(dashboard\) -name "page.tsx" -type f | while read p; do
  dir=$(dirname "$p")
  [ -f "$dir/loading.tsx" ] || echo "MISSING: $dir/loading.tsx"
done
Expected: 0 missing
Actual: ____ missing

Dynamic imports for cytoscape and react-markdown:
grep -rn "dynamic\|React.lazy" components/ --include="*.tsx" | head -10
Expected: cytoscape and react-markdown are dynamically imported
Actual: ____

═══════════════════════════════════════════════════════════════════
PHASE 10 — AC-8 MOBILE AUDIT (test at 375px)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-mobile-first

In browser DevTools, set viewport to 375px (iPhone 12).

For each dashboard page, verify:
□ Sidebar renders as Sheet drawer (not visible nav)
□ No horizontal overflow (DevTools → Elements → check overflow)
□ All touch targets ≥ 44px height (use DevTools measuring tool)
□ Pricing cards stack vertically
□ Mobile menu opens and closes correctly

Record PASS/FAIL for each check.

═══════════════════════════════════════════════════════════════════
FIX PRIORITY TABLE
═══════════════════════════════════════════════════════════════════

Fix violations in this EXACT order:

P0 — CRITICAL (fix immediately, do not pass go):
- Any page that crashes or shows 500 error
- Missing skip links on any page
- Hardcoded hex colors in component files (AC-1i)
- Sidebar not using bg-primary in both modes (AC-1a)

P1 — HIGH (fix before marking complete):
- Cards using rounded-lg instead of rounded-2xl (AC-3a)
- CTAs using rounded-md instead of rounded-full (AC-3b)
- H1 without font-serif (AC-2a)
- H2 without font-serif (AC-2b)
- ◆ mono labels without font-mono (AC-2d)
- Missing loading.tsx files (AC-7e)

P2 — MEDIUM (fix if found):
- Missing micro-interactions (hover states) (AC-4)
- Focus ring missing or wrong color (AC-1g)
- Missing aria-live on streaming content (AC-6e)
- axe-cli critical violations (AC-6f-h)
- Missing alt text on images (AC-6b)

P3 — LOW (fix if quick):
- Touch target < 44px on non-critical elements (AC-8a)
- Minor visual drift from spec

═══════════════════════════════════════════════════════════════════
ANTI-PATTERNS — automatic rejection without asking
═══════════════════════════════════════════════════════════════════

During this audit, if you find ANY of these, fix immediately and document:

❌ className with hardcoded hex color → replace with CSS variable immediately
❌ className="rounded-lg" on any card → change to rounded-2xl immediately
❌ className="rounded-md" on any CTA button → change to rounded-full immediately
❌ className="bg-white" → change to bg-card or bg-background immediately
❌ className="bg-background" on sidebar → must be bg-primary immediately
❌ className without font-serif on h1 or h2 → add font-serif immediately
❌ ◆ label without font-mono → add font-mono immediately
❌ Page without loading.tsx → create immediately
❌ Marketing pages without Header or Footer → add immediately
❌ Any hardcoded color (#1a1a1a, #ffffff, etc.) in className → replace immediately

═══════════════════════════════════════════════════════════════════
STORY-038-AUDIT.md — REQUIRED DOCUMENTATION
═══════════════════════════════════════════════════════════════════

After fixing all violations, create this file:

docs/stories/EPIC-08-polish/STORY-038-AUDIT.md

Use this EXACT format:

```markdown
# STORY-038 Audit Results

Date: [YYYY-MM-DD]
Agent: [agent identifier]
Build: [npm run build result]
Tests: [npm run test result]

## Phase 1: Hardcoded Hex Audit (AC-1i)

Command: grep -rn "#2d4a3e\|#f5f3ee..." [full command]
Violations found: [N]

| File | Line | Content | Fix Applied |
|---|---|---|---|
| path/to/file.tsx | 42 | "className=\"bg-[#2d4a3e]\"" | Replaced with bg-primary |

## Phase 2: CSS Variables Verification

:root tokens: [PASS/FAIL — list any missing/wrong]
.dark tokens: [PASS/FAIL — list any missing/wrong]
@theme inline fonts: [PASS/FAIL]

## Phase 3: Brand Color Audit (AC-1)

| Sub-item | Command | Expected | Actual | PASS/FAIL |
|---|---|---|---|---|
| AC-1a Sidebar bg-primary | grep... | >0 matches | N matches | PASS/FAIL |

## Phase 4: Typography Audit (AC-2)

| Sub-item | Command | Expected | Actual | PASS/FAIL |
|---|---|---|---|---|
| AC-2a H1 font-serif | grep... | 0 matches | N matches | PASS/FAIL |

## Phase 5: Shape Audit (AC-3)

| Sub-item | Command | Expected | Actual | PASS/FAIL |
|---|---|---|---|---|
| AC-3a cards rounded-2xl | grep... | 0 matches | N matches | PASS/FAIL |

## Phase 6: Micro-Interactions (AC-4)

| Sub-item | File | PASS/FAIL | Notes |
|---|---|---|---|
| AC-4a button hover | Button.tsx | PASS/FAIL | |

## Phase 7: Page-by-Page Audit (AC-5)

| Page | Brand | Typography | Shapes | Required | PASS/FAIL |
|---|---|---|---|---|---|
| /register | OK | OK | OK | OK | PASS |
| /login | ISSUES | OK | OK | MISSING | FAIL |

## Phase 8: Accessibility (AC-6)

| Page | Critical | Serious | Moderate | PASS/FAIL |
|---|---|---|---|---|
| / | 0 | 0 | 0 | PASS |
| /onboarding | 0 | 0 | 0 | PASS |
| /graph | 0 | 0 | 0 | PASS |

## Phase 9: Performance (AC-7)

| Check | Expected | Actual | PASS/FAIL |
|---|---|---|---|
| npm run build | 0 errors | N errors | PASS/FAIL |
| npm run test | 0 failures | N failures | PASS/FAIL |
| console.error/warn | 0 matches | N matches | PASS/FAIL |
| loading.tsx present | all present | N missing | PASS/FAIL |

## Phase 10: Mobile (AC-8)

| Page | Sidebar Sheet | No Overflow | 44px Targets | PASS/FAIL |
|---|---|---|---|---|
| /chat | PASS | PASS | FAIL | FAIL |
| /graph | PASS | PASS | PASS | PASS |

## Summary

Total violations found: [N]
Total violations fixed: [N]
Total violations outstanding: [N]

All P0 violations: FIXED ✅
All P1 violations: FIXED ✅ / [list if any remain]
All P2 violations: FIXED ✅ / [list if any remain]
All P3 violations: FIXED ✅ / [list if any remain]

Overall: [PASS/FAIL]
```

═══════════════════════════════════════════════════════════════════
SUCCESS CRITERIA — ALL must be YES to report complete
═══════════════════════════════════════════════════════════════════

INVOKE: Use /superpowers:verification-before-completion

✅ npm run build: 0 TypeScript errors, 0 warnings
✅ npm run test: 0 failures
✅ AC-1: 0 hardcoded hex violations in component files
✅ AC-2: 0 typography violations (all headlines font-serif, all mono labels font-mono)
✅ AC-3: 0 shape violations (all cards rounded-2xl, all CTAs rounded-full)
✅ AC-4: All micro-interactions present (verified in browser)
✅ AC-5: All 15 pages PASS page-by-page audit
✅ AC-6: axe reports 0 critical violations on 3 key pages
✅ AC-7: No console.error/warn in production code, all loading.tsx present
✅ AC-8: Mobile audit passes (no overflow, 44px touch targets)
✅ STORY-038-AUDIT.md created with all sections filled in
✅ Product walked through /register → /onboarding → /chat → /graph → /workstation → /sources → /inbox without any page crashing or showing wrong colors

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

**Quick reference for this story:**

```bash
# 1. Quality gate:
npm run build && npm run test   # frontend must pass

# 2. Commit (if any fixes needed):
git add -A && git commit -m "fix(ravenbase): STORY-038 UX polish audit fixes"
git push

# 3. Mark complete:
# Edit docs/stories/epics.md → STORY-038 🔲 → ✅
# Update docs/.bmad/story-counter.txt → FRONTEND_COMPLETE
# Update docs/.bmad/project-status.md → Phase B complete, all 38 stories done
# Append entry to docs/.bmad/journal.md
git add docs/stories/epics.md docs/.bmad/story-counter.txt \
       docs/.bmad/project-status.md docs/.bmad/journal.md
git commit -m "docs: mark STORY-038 complete, Phase B frontend fully done"
git push
```

---

## Docs Update (after completion)

After localhost verification passes, update all four docs files in one commit:

1. **docs/stories/epics.md** — STORY-038: 🔲 → ✅ in EPIC-08 table
2. **docs/.bmad/story-counter.txt** — change contents to: `FRONTEND_COMPLETE`
3. **docs/.bmad/project-status.md** — Phase: "B complete" | Sprint: "38" | Status: "38/38 stories complete"
4. **docs/.bmad/journal.md** — append Sprint 38 entry:
   ```
   ## Sprint 38 — Final UX Polish Pass
   Story: STORY-038
   Completed: [date from git log --oneline -1]
   Summary: End-to-end UX audit covering brand color system, typography, shape audit,
            micro-interactions, page-by-page functional check, accessibility (axe-cli),
            performance, and mobile. All 37 previous stories verified for visual compliance.
   Violations found: [N] hardcoded hex colors, [N] missing font-serif, [N] wrong border-radius
   All violations: fixed and committed
   ```
