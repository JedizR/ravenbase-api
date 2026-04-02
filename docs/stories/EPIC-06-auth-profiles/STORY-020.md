# STORY-020: System Profile Switching (Omnibar /profile)

**Epic:** EPIC-06 — Authentication & System Profiles
**Priority:** P1
**Complexity:** Small
**Depends on:** STORY-019

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — profile switching UX story (no directly testable API requirement).

## Component
COMP-05: AuthSystem

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (no form tags, apiFetch, Tailwind only)
> 3. `docs/design/02-component-library.md` — Omnibar component spec (slash-command pattern)
> 4. `docs/design/03-screen-flows.md` — Dashboard layout showing profile switcher location
> 5. `docs/architecture/02-database-schema.md` — SystemProfile model and `system_profiles` table

---

## User Story
As a user, I want to switch between System Profiles instantly so that my queries are scoped to the right context.

## Context
- Omnibar: STORY-008 created the Omnibar component with `/profile` stub — implement the real handler here
- Profile model: `architecture/02-database-schema.md` — `system_profiles` table
- Dashboard layout: `design/03-screen-flows.md` — sidebar profile switcher location

## Acceptance Criteria
- [ ] AC-1: Profile switching via Omnibar: `/profile [name]` command fuzzy-matches existing profile names
- [ ] AC-2: Profile switcher also accessible via sidebar dropdown (DropdownMenu from shadcn)
- [ ] AC-3: Active profile shown in sidebar header with name + color badge (using profile.color field)
- [ ] AC-4: Profile switch updates React context immediately (< 50ms — pure client state, no API call)
- [ ] AC-5: All subsequent searches and generation requests include active `profile_id` in the request body
- [ ] AC-6: Cross-profile query: "Search all profiles" toggle in the Omnibar search command
- [ ] AC-7: CRUD for profiles in Settings → Profiles page (`GET/POST/PUT/DELETE /v1/profiles`)
- [ ] AC-8: Profile list fetched from API on mount and cached in `ProfileContext` — no re-fetch on every switch
- [ ] AC-9: Mobile: profile switcher dropdown accessible from the mobile sidebar drawer;
  dropdown trigger has minimum 44px height for touch usability
- [ ] AC-10: Settings → AI Models section shows two options ("Haiku 4.5 — Fast & efficient
  (default)" and "Sonnet 4.6 — Higher quality, costs more credits"), selected option
  highlighted with `border-primary bg-primary/5`, persisted via PATCH /v1/account/model-preference
- [ ] AC-11: Settings → Notifications section shows 3 toggles: "Welcome email" (default on), "Low credits warning" (default on), "Ingestion complete" (default on, with note "Only sent for files larger than 2MB"). Each toggle calls `PATCH /v1/account/notification-preferences` on change. Current state loaded from `GET /v1/users/me`.

## Technical Notes

### Files to Create (Frontend)
- `contexts/ProfileContext.tsx` — React context providing active profile and profile list
- `components/domain/ProfileSwitcher.tsx` — sidebar dropdown component
- `app/(dashboard)/settings/profiles/page.tsx` — profile CRUD UI

### Files to Modify (Frontend)
- `components/domain/Omnibar.tsx` — implement `/profile` command handler using ProfileContext
- `app/(dashboard)/layout.tsx` — wrap with `<ProfileContextProvider>`

### Files to Create (Backend) — if not created in STORY-019
- `src/api/routes/profiles.py` — `GET /v1/profiles`, `POST /v1/profiles`, `PUT /v1/profiles/{id}`, `DELETE /v1/profiles/{id}`
- `src/schemas/profile.py` — `ProfileResponse`, `ProfileCreate`, `ProfileUpdate` schemas

### Mobile

Profile switching uses the same dropdown trigger as desktop, inside the mobile drawer.
No separate mobile UI needed — the sidebar drawer inherits the desktop sidebar's
profile switcher. Ensure the dropdown trigger has `min-h-[44px]` for touch targets.

### Model Preference UI

```tsx
{[
  {
    value: "haiku",
    label: "Haiku 4.5",
    description: "Fast & efficient — recommended for most users",
    credits: "3 credits/chat · 18 credits/meta-doc",
    badge: "Default",
  },
  {
    value: "sonnet",
    label: "Sonnet 4.6",
    description: "Higher quality synthesis and reasoning",
    credits: "8 credits/chat · 45 credits/meta-doc",
    badge: "Pro",
  },
].map((option) => (
  <button
    key={option.value}
    onClick={() => updateModel(option.value)}
    className={`w-full p-4 rounded-xl border text-left transition-colors ${
      preferredModel === option.value
        ? "border-primary bg-primary/5"
        : "border-border hover:border-primary/40"
    }`}
  >
    <div className="flex items-center justify-between mb-1">
      <span className="font-medium text-sm">{option.label}</span>
      <Badge variant={option.badge === "Default" ? "secondary" : "outline"}>
        {option.badge}
      </Badge>
    </div>
    <p className="text-xs text-muted-foreground">{option.description}</p>
    <p className="text-xs font-mono text-muted-foreground mt-1">{option.credits}</p>
  </button>
))}
```

### Notification Preferences UI

```tsx
// Settings → Notifications section
// Three toggle rows using shadcn Switch component

const notificationOptions = [
  {
    key: "notify_welcome" as const,
    label: "Welcome email",
    description: "Sent once when you first create your account.",
  },
  {
    key: "notify_low_credits" as const,
    label: "Low credits warning",
    description: "Sent when your credit balance drops below 10% of your plan.",
  },
  {
    key: "notify_ingestion_complete" as const,
    label: "Ingestion complete",
    description: "Sent when a large file (>2MB) finishes processing.",
  },
]

{notificationOptions.map((opt) => (
  <div
    key={opt.key}
    className="flex items-center justify-between py-4 border-b border-border last:border-0"
  >
    <div className="flex-1 pr-4">
      <p className="text-sm font-medium">{opt.label}</p>
      <p className="text-xs text-muted-foreground mt-0.5">{opt.description}</p>
    </div>
    <Switch
      checked={preferences[opt.key]}
      onCheckedChange={(checked) => updatePreference(opt.key, checked)}
      aria-label={opt.label}
    />
  </div>
))}
```

The `updatePreference` function calls `PATCH /v1/account/notification-preferences`
with only the changed field. Use optimistic update — flip the toggle immediately,
revert on API error with a `toast.error()`. No loading state needed (toggle is instant).

### Architecture Constraints
- Profile switching is pure client state — no API call on switch (the profile list is already loaded)
- `profile_id` injected into all `apiFetch` calls via `ProfileContext.activeProfile.id`
- CRUD operations go through `apiFetch()` — never raw `fetch()`
- No `<form>` tags — Settings → Profiles page uses controlled inputs + onClick

### ProfileContext Pattern
```typescript
// contexts/ProfileContext.tsx
"use client";
import { createContext, useContext, useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface Profile {
  id: string;
  name: string;
  color: string | null;
  is_default: boolean;
}

interface ProfileContextValue {
  profiles: Profile[];
  activeProfile: Profile | null;
  setActiveProfile: (profile: Profile) => void;
  isLoading: boolean;
}

const ProfileContext = createContext<ProfileContextValue | null>(null);

export function ProfileContextProvider({ children }: { children: React.ReactNode }) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [activeProfile, setActiveProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiFetch<{ items: Profile[] }>("/v1/profiles").then((data) => {
      setProfiles(data.items);
      const defaultProfile = data.items.find((p) => p.is_default) ?? data.items[0];
      setActiveProfile(defaultProfile ?? null);
      setIsLoading(false);
    });
  }, []);

  return (
    <ProfileContext.Provider value={{ profiles, activeProfile, setActiveProfile, isLoading }}>
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error("useProfile must be used within ProfileContextProvider");
  return ctx;
}
```

## Definition of Done
- [ ] Sidebar dropdown shows all profiles; clicking switches active profile
- [ ] `/profile [name]` in Omnibar switches to matching profile
- [ ] Active profile shown in sidebar with color badge
- [ ] All API calls include `profile_id` from active profile
- [ ] Settings → Profiles page: create/edit/delete profiles
- [ ] `npm run build` passes (0 TypeScript errors)

## Testing This Story

```bash
# Frontend build check:
npm run build

# Manual test:
# 1. Open dashboard — verify "Work Profile" (default) shown in sidebar
# 2. Create a second profile in Settings → Profiles
# 3. Use /profile command in Omnibar to switch
# 4. Verify sidebar shows new profile name
# 5. Trigger a search — verify profile_id in Network tab request payload

# Backend profile CRUD:
curl -X GET http://localhost:8000/v1/profiles \
  -H "Authorization: Bearer YOUR_TOKEN"
# Expected: {"items": [...profiles...], "total": N, ...}
```

**Passing result:** Profile switching is instant (pure client state). API calls include correct `profile_id`. Profile CRUD works in Settings.

---

## Agent Implementation Brief

```
Implement STORY-020: System Profile Switching.

Read first:
1. CLAUDE.md (architecture rules)
2. docs/design/AGENT_DESIGN_PREAMBLE.md — NON-NEGOTIABLE visual rules, anti-patterns, and pre-commit checklist. Read fully before writing any JSX.
3. docs/design/00-brand-identity.md — logo spec, voice rules, mono label pattern
4. docs/design/01-design-system.md — all color tokens, typography
5. docs/design/CLAUDE_FRONTEND.md (no form tags, apiFetch pattern)
6. docs/design/02-component-library.md (Omnibar spec — /profile command)
7. docs/design/03-screen-flows.md (Dashboard layout — sidebar profile switcher)
8. docs/stories/EPIC-06-auth-profiles/STORY-020.md (this file)

Key constraints:
- Profile switching is PURE CLIENT STATE — no API call on switch
- Profiles loaded once on mount and cached in ProfileContext
- All apiFetch calls must include profile_id from active profile
- No <form> tags. Use div + onClick handlers everywhere.
- /v1/profiles endpoint created server-side with require_user dependency

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
git add -A && git commit -m "feat(ravenbase): STORY-020 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-020"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-020
git add docs/stories/epics.md && git commit -m "docs: mark STORY-020 complete"
```
