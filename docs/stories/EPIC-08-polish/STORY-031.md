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

## Definition of Done

- [ ] Toggle appears in dashboard header
- [ ] `.dark` class added/removed on `<html>` element
- [ ] Preference persisted to localStorage
- [ ] No flash of wrong theme on page load
- [ ] Marketing pages respect stored preference
- [ ] `npm run build` passes (0 TypeScript errors)

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

## Agent Implementation Brief

```
Implement STORY-031: Dark Mode Toggle.

Read first:
1. CLAUDE.md (frontend rules — especially RULE 9: no forced color mode)
2. docs/design/01-design-system.md (complete CSS token system for both modes)
3. docs/design/CLAUDE_FRONTEND.md (RULE 9: no className="dark" on route layouts)
4. docs/stories/EPIC-08-polish/STORY-031.md (this file)

Key constraints:
- Implement with localStorage + classList, NOT next-themes package
- No-flash inline script in <head> (must run before React hydrates)
- Remove any forced .dark/.light class from route group layouts
- ThemeToggle component in dashboard header (not settings page)
- Default = light mode

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
