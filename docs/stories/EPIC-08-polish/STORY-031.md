# STORY-031: Dark Mode Toggle

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Small
**Depends on:** STORY-001-WEB (web repo scaffold must exist)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — dark mode toggle story.

## Component
UI/Polish

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` (frontend rules — especially RULE 9: no forced color mode in route groups)
> 2. `docs/design/01-design-system.md` — complete CSS token system, dark/light values
> 3. `docs/design/CLAUDE_FRONTEND.md` — RULE 9: no forced color mode in route groups
> 4. `docs/stories/EPIC-08-polish/STORY-031.md` (this file)

---

## User Story

As a user, I want to toggle between light and dark mode so I can use Ravenbase
comfortably in different lighting conditions.

## Context

- Color system: `docs/design/01-design-system.md` — both `:root` and `.dark` token sets
- Both themes are already defined in `globals.css`
- Default is LIGHT mode — dark is toggled by adding `.dark` to `<html>`
- Preference is persisted to localStorage
- No `next-themes` package — implement directly with localStorage + classList

## Acceptance Criteria

- [ ] AC-1: Dark mode toggle button appears in the dashboard header (top right, near avatar)
- [ ] AC-2: Toggle adds/removes `.dark` class on `document.documentElement`
- [ ] AC-3: User preference persisted to `localStorage` key `ravenbase-theme`
- [ ] AC-4: On page load, preference restored from localStorage before first paint (no flash)
- [ ] AC-5: Toggle shows Sun icon in dark mode (click to go light), Moon icon in light mode (click to go dark)
- [ ] AC-6: Marketing pages (landing, pricing) also respect the stored theme preference
- [ ] AC-7: Default is light mode if no preference is stored
- [ ] AC-8: Mobile: toggle button visible in mobile header (not hidden behind a menu);
  touch target is minimum 44px

## Technical Notes

### Files to Create
- `hooks/use-theme.ts` — theme state hook with localStorage persistence

### Files to Modify
- `app/layout.tsx` — add inline script in `<head>` for no-flash
- `app/(dashboard)/layout.tsx` — add `<ThemeToggle />` in header (REMOVE any forced `.dark` class)
- `app/(marketing)/layout.tsx` — REMOVE any forced `.light` class

### No-Flash Implementation

```tsx
// app/layout.tsx — inline script in <head> before any rendering
// Prevents flash of wrong theme on page load
<script
  dangerouslySetInnerHTML={{
    __html: `
      (function() {
        const stored = localStorage.getItem('ravenbase-theme');
        if (stored === 'dark') {
          document.documentElement.classList.add('dark');
        }
      })();
    `,
  }}
/>
```

### Theme Hook

```typescript
// hooks/use-theme.ts
"use client";
import { useEffect, useState } from "react";

export function useTheme() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Read stored preference
    const stored = localStorage.getItem("ravenbase-theme");
    const prefersDark = stored === "dark";
    setIsDark(prefersDark);
    document.documentElement.classList.toggle("dark", prefersDark);
  }, []);

  const toggle = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("ravenbase-theme", next ? "dark" : "light");
  };

  return { isDark, toggle };
}
```

### Toggle Button Component

```tsx
// components/domain/ThemeToggle.tsx — using pattern from BrandStyleGuide
"use client";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/use-theme";

export function ThemeToggle() {
  const { isDark, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary
                 hover:bg-accent transition-colors text-xs font-mono
                 text-muted-foreground border border-border"
      aria-label="Toggle dark mode"
    >
      {isDark
        ? <Moon className="w-3.5 h-3.5 text-primary" />
        : <Sun className="w-3.5 h-3.5 text-primary" />
      }
      <span className="hidden sm:inline">{isDark ? "Night" : "Day"}</span>
    </button>
  );
}
```

### Architecture Constraints

- No `next-themes` package — implement directly with localStorage + classList
- No `"use client"` on layout files — `ThemeToggle` component handles its own client boundary
- The inline `<script>` in `<head>` is the only way to prevent flash; this is acceptable
- Dark mode toggle belongs in the dashboard header, NOT in settings (accessibility)
- Sidebar remains `bg-primary` (forest green) in both light and dark mode

## UX & Visual Quality Requirements (mandatory — agent must complete ALL of these)

### Brand Color Verification (do this FIRST before any dark mode work)
Before implementing the toggle, verify and fix the brand color system:

1. Open app/globals.css and confirm these exact CSS variable values exist
   in the :root block. If wrong or missing, fix them:

   --background: #f5f3ee;           /* warm cream */
   --foreground: #1a1a1a;
   --card: #ffffff;
   --card-foreground: #1a1a1a;
   --primary: #2d4a3e;              /* forest green */
   --primary-foreground: #ffffff;
   --secondary: #e8ebe6;
   --secondary-foreground: #1a1a1a;
   --muted: #e8ebe6;
   --muted-foreground: #6b7280;
   --accent: #a8c4b2;
   --accent-foreground: #1a1a1a;
   --warning: #ffc00d;
   --warning-foreground: #78350f;
   --success: #3d8b5a;
   --success-foreground: #ffffff;
   --destructive: #b53233;
   --destructive-foreground: #ffffff;
   --border: #d1d5db;
   --input: #d1d5db;
   --ring: #2d4a3e;
   --radius: 1rem;                  /* 16px = rounded-2xl */

   .dark {
     --background: #1a1a1a;
     --foreground: #f5f3ee;
     --card: #242424;
     --card-foreground: #f5f3ee;
     --primary: #3d6454;            /* lighter forest green for dark bg contrast */
     --primary-foreground: #f0f7f4;
     --secondary: #2a2a2a;
     --secondary-foreground: #e8ebe6;
     --muted: #2a2a2a;
     --muted-foreground: #9ca3af;
     --accent: #2d4a3e;
     --accent-foreground: #a8c4b2;
     --warning: #ffc93d;
     --warning-foreground: #1a1a1a;
     --success: #4caf6c;
     --success-foreground: #1a1a1a;
     --destructive: #ef4444;
     --destructive-foreground: #ffffff;
     --border: #333333;
     --input: #333333;
     --ring: #3d6454;
   }

2. Confirm the @theme inline block correctly maps to next/font CSS variables:
   @theme inline {
     --font-sans: var(--font-dm-sans), "DM Sans", sans-serif;
     --font-serif: var(--font-playfair-display), "Playfair Display", Georgia, serif;
     --font-mono: var(--font-jetbrains-mono), "JetBrains Mono", monospace;
   }

3. Confirm app/layout.tsx applies font variables to <html>:
   className={`${dmSans.variable} ${playfairDisplay.variable} ${jetbrainsMono.variable}`}

4. After confirming/fixing the above, verify visual output:
   npm run dev
   Visit http://localhost:3000
   - Background must be warm cream #f5f3ee (NOT white, NOT gray)
   - If still wrong: run rm -rf .next && npm run dev

### Dark Mode Toggle Implementation Requirements

5. No flash of wrong theme on page load. Add this blocking script
   to <head> in app/layout.tsx BEFORE any stylesheets:
   <script dangerouslySetInnerHTML={{ __html: `
     (function(){
       try {
         var s = localStorage.getItem('ravenbase-color-scheme');
         var d = window.matchMedia('(prefers-color-scheme: dark)').matches;
         if (s === 'dark' || (!s && d)) {
           document.documentElement.classList.add('dark');
         }
       } catch(e) {}
     })();
   `}} />

6. Smooth color transition on toggle (no jarring flash):
   Add to globals.css:
   html.transitioning * {
     transition: background-color 200ms ease, border-color 200ms ease,
                 color 150ms ease !important;
   }
   When toggling, add 'transitioning' class to html, remove after 250ms.

7. Toggle button in DashboardHeader:
   - Sun icon (Lucide Sun) when dark mode is active, click → light
   - Moon icon (Lucide Moon) when light mode is active, click → dark
   - Icon rotates 180deg on toggle: className="transition-transform duration-300"
   - Button: className="p-2 rounded-lg hover:bg-secondary transition-colors min-h-[44px] min-w-[44px]"
   - Store preference in localStorage key: 'ravenbase-color-scheme'
   - Sync with system preference if no localStorage value

8. Dark mode sidebar: sidebar must remain bg-primary (forest green)
   in BOTH light and dark mode. Never use bg-background on sidebar.

9. Every existing CSS color in the codebase that is hardcoded (not using
   CSS variables) must be updated to use the design token. Search for:
   grep -r "#2d4a3e\|#f5f3ee\|#e8ebe6\|#ffc00d" components/ app/
   Replace all hardcoded hex values with the corresponding CSS variable.

## Definition of Done

- [ ] Toggle appears in dashboard header
- [ ] `.dark` class added/removed on `<html>` element
- [ ] Preference persisted to localStorage
- [ ] No flash of wrong theme on page load
- [ ] Marketing pages respect stored preference
- [ ] `npm run build` passes (0 TypeScript errors)

## Final Localhost Verification (mandatory before marking complete)

After `npm run build` passes and all tests pass, verify the running application works:

**Step 1 — Clear stale cache:**
```bash
rm -rf .next
```

**Step 2 — Start dev server:**
```bash
npm run dev
```

**Step 3 — Verify no runtime errors:**
- Open http://localhost:3000 in the browser
- Sign in if redirected to /login
- Navigate to any dashboard page (e.g., `/inbox`)
- Confirm NO "Internal Server Error" or webpack runtime errors
- Confirm CSS loads correctly (no unstyled content)
- Open browser DevTools → Console tab
- Confirm no red errors (yellow warnings acceptable)

**Step 4 — Report one of:**
- ✅ `localhost verified` — page renders correctly
- ⚠️ `Issue found: [describe issue]` — fix before committing docs

Only commit the docs update (epics.md, story-counter, project-status, journal) AFTER localhost verification passes.

## Testing This Story

```bash
# Build check:
npm run build

# Manual test:
# 1. Load app — verify light mode (cream background #f5f3ee, green sidebar)
# 2. Click toggle — verify dark mode (dark background #1a1a1a, adjusted green sidebar)
# 3. Refresh — verify dark mode persists
# 4. Open new tab — verify same preference
# 5. Toggle back — verify light mode
# 6. DevTools → localStorage → verify 'ravenbase-theme' key set to 'dark' or 'light'
# 7. Navigate to landing page — verify theme persists across routes
```

**Passing result:** Toggle switches between cream-background light mode and dark #1a1a1a dark mode. Preference persists across refreshes and new tabs. No flash on load.

---

## Frontend Agent Brief

> **Skill Invocations — MUST use these for each phase. Paste each skill call as a separate message before starting that phase:**
>
> **Phase 1 (Design):** `Use /frontend-design — before writing any JSX, this skill enforces production-grade aesthetic compliance`
> **Phase 2 (Implementation):** `Use /tailwindcss-mobile-first — for responsive layout verification`
> **Phase 3 (Accessibility):** `Use /tailwindcss-animations — for micro-interaction and transition patterns`
> **Phase 4 (Verification):** `Use /superpowers:verification-before-completion — before reporting complete`

---

```
🎯 Target: Claude Code / MiniMax-M2.7 — Structured step-by-step implementation prompt
💡 Optimized for: MiniMax-M2.7 (OpenAI-compatible, strong at instruction following, code generation, structured output)

═══════════════════════════════════════════════════════════════════
STEP 0 — PROJECT CONTEXT (carry forward to every phase)
═══════════════════════════════════════════════════════════════════

Ravenbase Frontend: Next.js 15 App Router + Tailwind CSS v4 + shadcn/ui + TanStack Query
Design system: CSS variables only (no hardcoded hex). Dark mode via .dark class on <html>
Brand colors: Primary=#2d4a3e (forest green), Background=#f5f3ee (warm cream), Accent=#a8c4b2
DO NOT introduce new design aesthetics — follow the established brand system exactly.

═══════════════════════════════════════════════════════════════════
STEP 1 — READ PHASE (mandatory — read ALL files before touching code)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /frontend-design

Then read ALL of these files in order — NOT in parallel — every file completely:

1. CLAUDE.md
   → Mandatory. All 19 rules. Especially RULE 5 (no forced color mode in route groups).

2. docs/design/AGENT_DESIGN_PREAMBLE.md
   → NON-NEGOTIABLE. Read every line. Anti-patterns to REJECT on sight:
     ❌ className="bg-[#2d4a3e]" → must be bg-primary
     ❌ className="rounded-lg" on cards → must be rounded-2xl
     ❌ className="rounded-md" on CTAs → must be rounded-full
     ❌ className=".dark" on layout outer div → forbidden
     ❌ next-themes package → forbidden (localStorage + classList only)

3. docs/design/00-brand-identity.md
   → Brand colors exact values, mono labels ◆ PATTERN, logo usage rules.

4. docs/design/01-design-system.md
   → Complete CSS variable definitions for :root and .dark. Read the entire file.
   → Section A: Conflict Card (Active) — border-2 border-primary
   → Section B: Memory Sticky Note — bg-[#fef9c3] rotation pattern

5. docs/design/04-ux-patterns.md
   → Micro-interaction specs: hover states, transitions, animations.
   → Keyboard navigation patterns.
   → IMPORTANT: This file specifies exact animation timings — use them.

6. docs/stories/EPIC-08-polish/STORY-031.md (this file)
   → All 8 ACs defined here. Implementation must satisfy all 8.

═══════════════════════════════════════════════════════════════════
STEP 2 — VERIFY CSS VARIABLES (Phase 2a — before creating any component)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss — for Tailwind CSS v4 token usage

Open app/globals.css. READ the entire file. Confirm ALL of these exist:

:root {
  --background: #f5f3ee;       /* warm cream — MUST be exact */
  --foreground: #1a1a1a;
  --primary: #2d4a3e;          /* forest green — MUST be exact */
  --primary-foreground: #ffffff;
  --secondary: #e8ebe6;
  --secondary-foreground: #1a1a1a;
  --muted: #e8ebe6;
  --muted-foreground: #6b7280;
  --accent: #a8c4b2;
  --accent-foreground: #1a1a1a;
  --warning: #ffc00d;
  --warning-foreground: #78350f;
  --success: #3d8b5a;
  --success-foreground: #ffffff;
  --destructive: #b53233;
  --destructive-foreground: #ffffff;
  --border: #d1d5db;
  --input: #d1d5db;
  --ring: #2d4a3e;
  --card: #ffffff;
  --card-foreground: #1a1a1a;
  --radius: 1rem;              /* = rounded-2xl in Tailwind */
}

.dark {
  --background: #1a1a1a;
  --foreground: #f5f3ee;
  --primary: #3d6454;          /* lighter green for dark bg */
  --primary-foreground: #f0f7f4;
  --secondary: #2a2a2a;
  --secondary-foreground: #e8ebe6;
  --muted: #2a2a2a;
  --muted-foreground: #9ca3af;
  --accent: #2d4a3e;
  --accent-foreground: #a8c4b2;
  --warning: #ffc00d;
  --warning-foreground: #1a1a1a;
  --success: #4caf6c;
  --success-foreground: #1a1a1a;
  --destructive: #ef4444;
  --destructive-foreground: #ffffff;
  --border: #333333;
  --input: #333333;
  --ring: #3d6454;
  --card: #242424;
  --card-foreground: #f5f3ee;
}

Also confirm @theme inline maps fonts:
@theme inline {
  --font-sans: var(--font-dm-sans), "DM Sans", sans-serif;
  --font-serif: var(--font-playfair-display), "Playfair Display", Georgia, serif;
  --font-mono: var(--font-jetbrains-mono), "JetBrains Mono", monospace;
}

IF ANY VARIABLE IS WRONG OR MISSING → fix globals.css FIRST.
This is a prerequisite for every subsequent step.

═══════════════════════════════════════════════════════════════════
STEP 3 — CREATE HOOK (Phase 2b — useTheme)
═══════════════════════════════════════════════════════════════════

File: hooks/use-theme.ts

"use client"
import { useEffect, useState } from "react"

const STORAGE_KEY = "ravenbase-theme"

export function useTheme() {
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    // AC-7: Default = light if nothing stored
    const stored = localStorage.getItem(STORAGE_KEY)
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
    const dark = stored === "dark" || (!stored && prefersDark)
    setIsDark(dark)
    document.documentElement.classList.toggle("dark", dark)
  }, [])

  const toggle = () => {
    // Add transitioning class for smooth animation
    document.documentElement.classList.add("transitioning")
    const next = !isDark
    setIsDark(next)
    document.documentElement.classList.toggle("dark", next)
    // AC-3: Persist to localStorage
    localStorage.setItem(STORAGE_KEY, next ? "dark" : "light")
    // Remove transitioning class after animation completes
    setTimeout(() => document.documentElement.classList.remove("transitioning"), 250)
  }

  return { isDark, toggle }
}

═══════════════════════════════════════════════════════════════════
STEP 4 — CREATE THEME TOGGLE COMPONENT (Phase 2c)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-animations

File: components/domain/ThemeToggle.tsx

"use client"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "@/hooks/use-theme"

export function ThemeToggle() {
  const { isDark, toggle } = useTheme()

  return (
    <button
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                 bg-secondary hover:bg-accent
                 text-xs font-mono text-muted-foreground
                 border border-border
                 min-h-[44px] min-w-[44px]   // AC-8: 44px touch target minimum
                 transition-colors duration-150"
    >
      {isDark ? (
        <Sun className="w-3.5 h-3.5 text-primary transition-transform duration-300 rotate-180" />
      ) : (
        <Moon className="w-3.5 h-3.5 text-primary transition-transform duration-300 rotate-0" />
      )}
      <span className="hidden sm:inline">{isDark ? "Day" : "Night"}</span>
    </button>
  )
}

═══════════════════════════════════════════════════════════════════
STEP 5 — ADD NO-FLASH SCRIPT (Phase 2d — app/layout.tsx)
═══════════════════════════════════════════════════════════════════

In app/layout.tsx <head> section — BEFORE any other scripts:

<script
  dangerouslySetInnerHTML={{
    __html: `
(function() {
  try {
    var s = localStorage.getItem('ravenbase-theme');
    var d = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (s === 'dark' || (!s && d)) {
      document.documentElement.classList.add('dark');
    }
  } catch(e) {}
})();
`,
  }}
/>

AC-4: This blocking script must run before React hydrates — prevents flash.

Also confirm <html> has:
className={`${dmSans.variable} ${playfair.variable} ${jetbrainsMono.variable}`}

═══════════════════════════════════════════════════════════════════
STEP 6 — FIX ROUTE GROUP LAYOUTS (Phase 2e)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-mobile-first

Search for any forced color mode in layouts:
grep -rn "className=.*.dark\|className=.*light" app/\(marketing\)/layout.tsx app/\(dashboard\)/layout.tsx

AC-6 REQUIREMENT: Marketing pages must respect stored theme preference.
→ REMOVE any className=".dark" or className=".light" from the marketing layout outer div.
→ REMOVE any className=".dark" from dashboard layout outer div.

Also add smooth transition to globals.css (if not already present):
html.transitioning,
html.transitioning * {
  transition: background-color 200ms ease, border-color 200ms ease,
              color 150ms ease !important;
}

═══════════════════════════════════════════════════════════════════
STEP 7 — ADD TOGGLE TO DASHBOARD HEADER (Phase 2f)
═══════════════════════════════════════════════════════════════════

Find the dashboard header component. Common locations:
- components/domain/DashboardHeader.tsx
- app/(dashboard)/layout.tsx (inline)

Add <ThemeToggle /> in the top-right area of the header, near the user avatar.

AC-1: Toggle must appear in dashboard header (top right, near avatar).

═══════════════════════════════════════════════════════════════════
STEP 8 — VERIFY SIDEBAR (Phase 2g)
═══════════════════════════════════════════════════════════════════

AC-1 (critical): Sidebar must remain bg-primary (#2d4a3e forest green) in BOTH light
and dark mode. NEVER use bg-background or bg-sidebar on the sidebar.

Search: grep -rn "bg-primary" app/\(dashboard\)/ | grep -i sidebar
Confirm: sidebar nav container has className containing "bg-primary"

═══════════════════════════════════════════════════════════════════
STEP 9 — HARDCODE HEX AUDIT (Phase 3 — Accessibility & Quality)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /superpowers:verification-before-completion

Run this audit and fix ALL violations before proceeding:
grep -rn "#2d4a3e\|#f5f3ee\|#e8ebe6\|#ffc00d\|#a8c4b2\|#1a1a1a" \
  components/ app/ --include="*.tsx" --include="*.ts"

Every match must be:
  ✅ Inside app/globals.css as a CSS variable definition
  ✅ In a comment explaining the brand color
NOT in any className string in a component file.

If found in a className → replace with CSS variable:
  #2d4a3e → bg-primary
  #f5f3ee → bg-background
  #e8ebe6 → bg-secondary
  #a8c4b2 → bg-accent
  #ffc00d → bg-warning
  #1a1a1a → text-foreground (or bg-foreground in dark contexts)

═══════════════════════════════════════════════════════════════════
STEP 10 — VERIFY ALL 8 ACCEPTANCE CRITERIA (Phase 4)
═══════════════════════════════════════════════════════════════════

For each AC, write a one-line verification result:

□ AC-1: ThemeToggle in dashboard header — VERIFIED (grep confirms <ThemeToggle in header)
□ AC-2: .dark class on documentElement — VERIFIED (useTheme.ts calls classList.toggle)
□ AC-3: localStorage persists 'dark'/'light' — VERIFIED (grep confirms STORAGE_KEY)
□ AC-4: No-flash script in <head> — VERIFIED (grep confirms <script dangerouslySetInnerHTML in layout)
□ AC-5: Sun/Moon icon swap — VERIFIED (ThemeToggle renders both icons conditionally)
□ AC-6: Marketing respects theme — VERIFIED (grep: no forced .dark/.light in marketing layout)
□ AC-7: Default = light — VERIFIED (useTheme: stored === null → light)
□ AC-8: 44px touch target — VERIFIED (className: min-h-[44px] min-w-[44px])
□ Brand: sidebar bg-primary in both modes — VERIFIED (grep confirms)
□ Hex audit: 0 violations — VERIFIED (grep run, 0 matches in component files)

═══════════════════════════════════════════════════════════════════
WHAT NOT TO DO (Anti-patterns — reject these on sight)
═══════════════════════════════════════════════════════════════════

❌ DO NOT use next-themes package — localStorage + classList only
❌ DO NOT add className="dark" or "light" to any layout outer div
❌ DO NOT use bg-[#2d4a3e] — use bg-primary
❌ DO NOT use bg-[#f5f3ee] — use bg-background
❌ DO NOT use rounded-lg on cards — rounded-2xl only
❌ DO NOT use rounded-md on CTAs — rounded-full only
❌ DO NOT put ThemeToggle in Settings — header only
❌ DO NOT use system color scheme as sole determinant — localStorage takes priority

═══════════════════════════════════════════════════════════════════
SUCCESS CRITERIA — ALL must be YES to report complete
═══════════════════════════════════════════════════════════════════

✅ npm run build passes (0 TypeScript errors)
✅ AC-1 through AC-8 all verified
✅ Sidebar: bg-primary in both light and dark mode
✅ No hardcoded hex colors in any component file
✅ No flash on page load (blocking script confirmed)
✅ Theme toggle: Sun in dark mode, Moon in light mode
✅ localStorage key 'ravenbase-theme' persists preference
✅ Marketing pages respect stored theme (no forced mode)

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

```bash
npm run build && npm run test
git add -A && git commit -m "feat(ravenbase): STORY-031 dark mode toggle"
git push
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-031
git add docs/stories/epics.md && git commit -m "docs: mark STORY-031 complete"
git push
```
