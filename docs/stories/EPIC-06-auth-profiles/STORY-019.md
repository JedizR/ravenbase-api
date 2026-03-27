# STORY-019: Onboarding Wizard

**Epic:** EPIC-06 — Authentication & System Profiles
**Priority:** P0
**Complexity:** Medium
**Depends on:** STORY-018

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — onboarding UX story (no directly testable API requirement).

## Component
COMP-05: AuthSystem

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (no form tags, Tailwind only, apiFetch)
> 3. `docs/design/03-screen-flows.md` — Onboarding Wizard screen layout (3-step flow)
> 4. `docs/architecture/02-database-schema.md` — User model (has_completed_onboarding field)
> 5. `docs/architecture/03-api-contract.md` — ingest/upload and ingest/text endpoints

---

## User Story
As a new user, I want a guided onboarding experience so I understand what Ravenbase does and upload my first file within 5 minutes.

## Context
- Screen flow: `design/03-screen-flows.md` — Onboarding Wizard 3-step layout
- API: STORY-018 auth (upload endpoints require JWT)
- API: STORY-007 SSE progress stream (used in Step 3)
- Data model: `architecture/02-database-schema.md` — User.has_completed_onboarding

## Acceptance Criteria
- [ ] AC-1: 3-step wizard at `/onboarding`: (1) Name your first System Profile, (2) Upload first file or paste text, (3) Wait for processing → enter dashboard
- [ ] AC-2: Step 1: Role selection (Software Engineer, Student, Designer, Researcher, Other) + profile name input
- [ ] AC-3: Step 2: Drag-and-drop file upload (uses `IngestionDropzone` component) OR text paste textarea
- [ ] AC-4: Step 3: Progress bar connected to SSE stream — auto-advances to `/dashboard` when `status=completed`
- [ ] AC-5: "Skip for now" option on Step 2 that goes directly to `/dashboard`
- [ ] AC-6: Onboarding completion stored in PostgreSQL (`User.has_completed_onboarding = true`)
- [ ] AC-7: Completed users skip onboarding on subsequent logins (middleware check)
- [ ] AC-8: Step indicator visible at top (1/3, 2/3, 3/3) using shadcn Progress
- [ ] AC-9: Mobile (< 640px): all three wizard steps render correctly at 375px
  with no horizontal overflow; step indicator and navigation buttons visible without scrolling
- [ ] AC-10: After `router.push("/dashboard")`, the URL is `/dashboard?first_run=true` — the `?first_run=true` query param signals the dashboard to show the GettingStartedChecklist for new users
- [ ] AC-11: "Skip for now" redirects to `/dashboard?first_run=true` as well — the checklist renders regardless of whether the user uploaded or skipped

## Technical Notes

### Files to Create (Frontend)
- `app/(auth)/onboarding/page.tsx` — 3-step wizard container
- `components/domain/OnboardingWizard.tsx` — step components (StepProfile, StepUpload, StepProgress)

### Files to Modify (Backend)
- `src/models/user.py` — add `has_completed_onboarding: bool = Field(default=False)`
- `alembic/versions/` — new migration: `add_has_completed_onboarding_to_users`
- `src/api/routes/` — add endpoint `POST /v1/users/me/complete-onboarding` to set flag

### Mobile Layout

The onboarding wizard is a centered card. On mobile, it becomes full-screen:

```tsx
{/* Full-screen on mobile, centered card on desktop */}
<div className="min-h-screen flex items-center justify-center p-4 sm:p-6">
  <div className="w-full max-w-md bg-card rounded-2xl sm:border sm:border-border p-6">
    {/* wizard content */}
  </div>
</div>
```

Role selector grid: `grid grid-cols-2 gap-2` stays at 2 columns on mobile (works at 375px).

### Architecture Constraints
- No `<form>` tags — use `div` with `onClick` handlers
- File upload calls `POST /v1/ingest/upload` via `apiFetch()` — no raw fetch
- SSE progress uses `useSSE` hook from `hooks/use-sse.ts` (created in STORY-017)
- Onboarding route is under `(auth)/` group (light mode, auth required after Clerk login)
- `has_completed_onboarding = true` set via API call, NOT directly from frontend — route handler calls service

### Onboarding Completion Pattern
```typescript
// After file upload or skip:
await apiFetch("/v1/users/me/complete-onboarding", { method: "POST" });
router.push("/dashboard");
```

### First-Run Redirect Pattern

```typescript
// After file upload completes OR skip:
await apiFetch("/v1/users/me/complete-onboarding", { method: "POST" });
// Always append ?first_run=true — dashboard uses this to show GettingStartedChecklist
router.push("/dashboard?first_run=true");
```

The dashboard reads `searchParams.get("first_run")` on mount, shows the checklist if
present, then immediately calls `router.replace("/dashboard")` to clean the URL.
See `docs/design/04-ux-patterns.md` → "First-Run Dashboard Experience" for the full spec.

## Definition of Done
- [ ] New user completes all 3 steps and reaches `/dashboard`
- [ ] "Skip for now" button works and sets `has_completed_onboarding = true`
- [ ] Returning users (`has_completed_onboarding = true`) bypass `/onboarding` on login
- [ ] `make quality` passes (0 errors on new endpoint)
- [ ] `npm run build` passes (0 TypeScript errors)

## Testing This Story

```bash
# Frontend build:
npm run build

# Manual test flow:
# 1. Register new user at /register
# 2. Verify redirect to /onboarding
# 3. Complete Step 1 (role + profile name)
# 4. Complete Step 2 (upload a small PDF or paste text)
# 5. Watch Step 3 progress bar advance
# 6. Verify auto-redirect to /dashboard
# 7. Log out, log back in → verify /onboarding is skipped

# Backend: verify flag set
make quality
uv run pytest tests/integration/api/test_onboarding.py -v
```

**Passing result:** User completes onboarding, `users.has_completed_onboarding = true` in DB, subsequent login skips wizard.

---

## Agent Implementation Brief

```
Implement STORY-019: Onboarding Wizard.

Read first:
1. CLAUDE.md (architecture rules)
2. docs/design/CLAUDE_FRONTEND.md (no form tags, Tailwind only, apiFetch)
3. docs/design/03-screen-flows.md (Onboarding Wizard 3-step layout diagram)
4. docs/architecture/02-database-schema.md (User model — add has_completed_onboarding)
5. docs/stories/EPIC-06-auth-profiles/STORY-019.md (this file)

Key constraints:
- No <form> tags. Use div + onClick handlers.
- File upload via apiFetch("/v1/ingest/upload") — not raw fetch
- SSE progress via useSSE hook (reuse from STORY-017)
- has_completed_onboarding set via API call (not direct DB write from frontend)
- Requires a new Alembic migration for the new column

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
git add -A && git commit -m "feat(ravenbase): STORY-019 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-019"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-019
git add docs/stories/epics.md && git commit -m "docs: mark STORY-019 complete"
```
