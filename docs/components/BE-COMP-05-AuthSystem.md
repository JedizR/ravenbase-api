# AuthSystem

> **Component ID:** BE-COMP-05
> **Epic:** EPIC-06 — Authentication & System Profiles
> **Stories:** STORY-018, STORY-019, STORY-020
> **Type:** Cross-repo (Backend + Frontend)

---

## Purpose

The AuthSystem is the thin authentication boundary for Ravenbase. On the backend: validates Clerk JWTs via JWKS endpoint, handles Clerk webhooks to provision/deprovision User records, and provides the `require_user` FastAPI dependency used by every protected route. On the frontend: Clerk `<SignIn>`/`<SignUp>` pages with Ravenbase branding, `middleware.ts` that protects dashboard routes, and `apiFetch`/`useApiFetch` wrappers that attach Bearer tokens to all API calls.

---

## User Journey

**New user registration:**
1. Visitor clicks "Start for free" → navigates to `/register`
2. Clerk `<SignUp>` component renders inside Ravenbase-branded card
3. User signs up → Clerk fires `user.created` webhook → `POST /webhooks/clerk`
4. Backend creates `User` record in PostgreSQL with `id = clerk_user_id` + 500 credits
5. `afterSignUpUrl="/onboarding"` in `<SignUp>` component prop → user redirected to `/onboarding`
6. OnboardingWizard: user creates first System Profile → optionally uploads first file
7. Completion: `router.push("/chat")` ← CORRECT (NOT `/dashboard`)

**Returning user sign-in:**
1. User visits `/login` → Clerk `<SignIn>` renders
2. Signs in → `afterSignInUrl="/chat"` → directed to `/chat` dashboard

**Unauthenticated user visiting protected route:**
1. User visits `/chat` without session
2. `middleware.ts` detects no `userId` → redirect to `/login`

**Authenticated user visiting landing page:**
1. User visits `/` while logged in
2. `middleware.ts` detects `userId` + `pathname === "/"` → redirect to `/chat`

---

## Admin Bypass

No credits consumed in auth operations — bypass not needed.

Admin users follow the same auth flow as regular users. The only admin-specific behavior is the `is_admin: boolean` field in `GET /v1/me` which the frontend uses to show `◆ ADMIN_ACCESS` in the sidebar.

**How to implement `is_admin` in `GET /v1/me`:**
```python
# In src/api/routes/account.py (or wherever GET /v1/me lives):
admin_ids = {u.strip() for u in settings.ADMIN_USER_IDS.split(",") if u.strip()}
is_admin = str(user.id) in admin_ids
return MeResponse(**user_data, is_admin=is_admin)
```

---

## Known Bugs / Current State

**BUG-004 (HIGH):** Authenticated users visiting `/` see the landing page instead of being redirected to `/chat`.
- **Root cause:** `ravenbase-web/middleware.ts` only handles unauthenticated users visiting protected routes. It has no branch for authenticated users visiting the landing page.
- **Fix:**
  ```typescript
  // middleware.ts — add BEFORE the unauthenticated redirect:
  const { userId } = await auth()
  if (userId && request.nextUrl.pathname === "/") {
    return NextResponse.redirect(new URL("/chat", request.url))
  }
  ```
- **Story:** STORY-039

**BUG-005 (HIGH):** OnboardingWizard completion redirects to `/dashboard` → 404.
- **Root cause:** `components/domain/OnboardingWizard.tsx` (lines 97 and 134) calls `router.push("/dashboard")`. The route `/dashboard` does not exist — it is not a valid URL in the Next.js route group structure.
- **Fix:** Change all instances to `router.push("/chat")`.
- **Story:** STORY-039

**⚠️ ROUTE LOCATION WARNING:**
```
CORRECT location for onboarding: app/(auth)/onboarding/page.tsx
WRONG:  app/(dashboard)/onboarding/page.tsx
```
The onboarding page has NO sidebar, NO DashboardHeader. It lives under `(auth)` not `(dashboard)`.

**Stale docs references (non-code bugs):**
- `BE-COMP-05-AuthSystem.md` SubComp 05B says redirect to `/dashboard` (incorrect)
- `BE-COMP-05-AuthSystem.md` SubComp 05C lists route as `app/(dashboard)/onboarding/page.tsx` (incorrect)
- `SubComp 05C` says "Completion redirects to `/dashboard`" (incorrect — must be `/chat`)

---

## Acceptance Criteria

- [ ] Authenticated user visits `/` → immediately redirects to `/chat` (BUG-004 fixed)
- [ ] New user registers → Clerk webhook creates User + 500 credits in DB
- [ ] New user after registration → `/onboarding` (not `/chat` directly)
- [ ] OnboardingWizard completion → `router.push("/chat")` (BUG-005 fixed, not `/dashboard`)
- [ ] Unauthenticated user visits `/chat` → redirect to `/login`
- [ ] `/login` and `/register` render Clerk components with Ravenbase branding
- [ ] `require_user` dependency extracts `user_id` from JWT `sub` claim
- [ ] Expired JWT → `403 TOKEN_EXPIRED`
- [ ] Invalid JWT → `403 INVALID_TOKEN`
- [ ] Missing auth header → `401 MISSING_AUTH`
- [ ] Clerk webhook with invalid `svix` signature → `400`
- [ ] `GET /v1/me` returns `{is_admin: boolean}` based on `ADMIN_USER_IDS`
- [ ] SSE endpoints accept JWT via `?token=` query param

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `FE-COMP-03-OnboardingWizard.md` — onboarding route, BUG-005 fix details
- `BE-COMP-06-CreditSystem.md` — 500 signup credit bonus
- `docs/architecture/03-api-contract.md` — `/webhooks/clerk`, `GET /v1/me`
- `docs/components/REFACTOR_PLAN.md` — BUG-004, BUG-005 fix details

---

## Goal

The AuthSystem owns all JWT validation, Clerk webhook handling, and the `require_user`/`verify_token_query_param` FastAPI dependencies. It is a thin gateway — it handles no business logic, only authentication and authorization enforcement at the boundary. The frontend auth pages (SignIn/SignUp) and auth middleware are also part of this component.

---

## Product Requirements

1. **JWT Validation:** Every protected API endpoint uses the `require_user` FastAPI dependency which validates Clerk JWTs via JWKS endpoint. Expired tokens return `403 TOKEN_EXPIRED`. Invalid tokens return `403 INVALID_TOKEN`. Missing auth header returns `401`.

2. **tenant_id from JWT:** `tenant_id` is always extracted from the JWT `sub` claim. It is NEVER accepted from request body or query parameters.

3. **SSE Token Query Param:** SSE endpoints (`/v1/ingest/stream/{source_id}`) use `verify_token_query_param` — JWT passed as `?token=` query param since `EventSource` cannot set headers.

4. **Clerk Webhook — User Created:** `POST /webhooks/clerk` creates a `User` record in PostgreSQL on `user.created` event. User `id` MUST equal Clerk `user_id`. Webhook signature validated via `svix`.

5. **Clerk Webhook — User Deleted:** `user.deleted` event soft-deletes or removes the User record.

6. **SignIn/SignUp Pages:** Frontend `/login` and `/register` pages use Clerk `<SignIn>` and `<SignUp>` components wrapped in Ravenbase branding.

7. **Auth Middleware:** `middleware.ts` protects all `/dashboard/*` routes, redirecting unauthenticated users to `/login`.

8. **apiFetch Wrapper:** `lib/api.ts` (Server Components) and `lib/api-client.ts` (Client Components) attach Clerk Bearer token to all API requests.

9. **Onboarding Wizard:** New users are redirected to `/onboarding` after first login to create their first System Profile and optionally upload their first file.

10. **Profile Switching:** The Omnibar `/profile` command allows switching between System Profiles. All API calls scoped to the active `profile_id`.

---

## Criteria and Tests

| Criterion | Test |
|---|---|
| Missing auth header returns 401 | `curl /v1/graph/nodes` (no auth) → 401 |
| Expired token returns 403 TOKEN_EXPIRED | Use expired JWT → 403 with code TOKEN_EXPIRED |
| Invalid token returns 403 INVALID_TOKEN | Use malformed JWT → 403 with code INVALID_TOKEN |
| Valid JWT allows access | Use valid Clerk JWT → 200 with data |
| Clerk webhook creates User on signup | Trigger user.created → SELECT * FROM users WHERE id = clerk_user_id |
| Clerk webhook rejects unsigned payloads | POST to webhook without svix signature → 400 |
| SSE token in query param works | `?token=clerk_jwt` → SSE stream connects successfully |
| Dashboard redirects to /login when unauthenticated | GET /dashboard without auth → redirect to /login |
| New user redirected to /onboarding | First login with new Clerk account → redirect to /onboarding |
| Onboarding creates first System Profile | Complete onboarding → SELECT * FROM system_profiles |
| Profile switch updates active profile context | Switch profile via /profile command → subsequent calls use new profile_id |

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-018](../stories/EPIC-06-auth-profiles/STORY-018.md) | Clerk Auth Integration | Cross-repo | JWT validation, Clerk webhook, SignIn/SignUp pages, middleware |
| [STORY-019](../stories/EPIC-06-auth-profiles/STORY-019.md) | Onboarding Wizard | Frontend | Profile creation + first upload flow |
| [STORY-020](../stories/EPIC-06-auth-profiles/STORY-020.md) | Profile Switching | Cross-repo | Omnibar /profile command, active profile context |

---

## Subcomponents

The AuthSystem decomposes into 3 subcomponents.

---

### SUBCOMP-05A: JWT Validation + Clerk Webhooks

**Stories:** STORY-018 (backend portion)
**Files:** `src/api/dependencies/auth.py`, `src/api/routes/webhooks.py`, `src/models/user.py`

#### Details
The backend auth layer provides `require_user` (header-based) and `verify_token_query_param` (SSE query param) FastAPI dependencies. It validates Clerk JWTs against Clerk's JWKS endpoint using `jwt.PyJWKClient` with in-process caching. The Clerk webhook handler creates/updates User records on `user.created`/`user.deleted` events, with signatures validated via `svix`.

#### Criteria of Done
- [ ] `require_user(authorization: str | None = Header(None))` returns `{"user_id": sub, "email": ...}`
- [ ] Expired JWT → 403 `TOKEN_EXPIRED`
- [ ] Invalid JWT → 403 `INVALID_TOKEN`
- [ ] Missing auth header → 401
- [ ] JWKS client is module-level cached (`_get_jwks_client()`)
- [ ] `verify_token_query_param` extracts JWT from `?token=` query param for SSE endpoints
- [ ] `POST /webhooks/clerk` creates User on `user.created` with `id = payload["data"]["id"]`
- [ ] `POST /webhooks/clerk` rejects unsigned payloads with 400 via `svix`
- [ ] All protected routes use `require_user` dependency

#### Checklist
- [ ] `jwt.PyJWKClient` created once, cached in module-level `_clerk_jwks_client`
- [ ] `jwt.decode()` with `algorithms=["RS256"]` and `options={"verify_exp": True}`
- [ ] Error codes: `MISSING_AUTH` (401), `TOKEN_EXPIRED` (403), `INVALID_TOKEN` (403)
- [ ] `svix.Webhook` validates `raw_body` and `headers` from Clerk webhook
- [ ] `User` record created with `id = clerk_user_id` (NOT generated UUID)
- [ ] `user.deleted` event: soft-delete or cascade-delete User
- [ ] Required env vars: `CLERK_FRONTEND_API`, `CLERK_WEBHOOK_SECRET`

#### Testing
```bash
# Missing auth:
curl http://localhost:8000/v1/graph/nodes
# Expected: 401 {"detail": {"code": "MISSING_AUTH"}}

# Invalid token:
curl http://localhost:8000/v1/graph/nodes -H "Authorization: Bearer invalid.token.here"
# Expected: 403 {"detail": {"code": "INVALID_TOKEN"}}

# Valid token:
curl http://localhost:8000/v1/graph/nodes -H "Authorization: Bearer VALID_JWT"
# Expected: 200 {"nodes": [], "edges": []}

# Webhook test (requires Clerk CLI):
# clerk log tail --forward-to http://localhost:8000/webhooks/clerk
# Create test user in Clerk dashboard
# psql -c "SELECT * FROM users WHERE email = 'test@example.com'"
# Expected: User row exists
```

---

### SUBCOMP-05B: Frontend Auth Pages + Middleware

**Stories:** STORY-018 (frontend portion)
**Files:** `app/(auth)/login/page.tsx`, `app/(auth)/register/page.tsx`, `app/(auth)/layout.tsx`, `lib/api.ts`, `lib/api-client.ts`, `middleware.ts`, `components/brand/RavenbaseLogo.tsx`, `components/brand/RavenbaseLockup.tsx`

#### Details
The frontend auth layer provides Clerk-wrapped SignIn/SignUp pages at `/login` and `/register`, an auth middleware that protects dashboard routes, and API fetch utilities that attach the Clerk Bearer token to all requests. The auth pages use warm cream backgrounds with centered Ravenbase branding wrapping the Clerk component.

#### Criteria of Done
- [ ] `/login` renders Clerk `<SignIn />` inside Ravenbase-branded card
- [ ] `/register` renders Clerk `<SignUp />` inside Ravenbase-branded card
- [ ] `(auth)/layout.tsx` sets light mode (no `.dark` class)
- [ ] Auth pages: warm cream background, `<RavenbaseLockup />` centered above Clerk component
- [ ] Clerk `<SignIn/SignUp>` inside `bg-card rounded-2xl shadow-sm`
- [ ] `middleware.ts` protects `/dashboard/*` → redirects to `/login` if unauthenticated
- [ ] `lib/api.ts` (Server): `apiFetch<T>()` using `auth().getToken()`
- [ ] `lib/api-client.ts` (Client): `useApiFetch()` hook using `useAuth().getToken()`
- [ ] After login: redirect to `/chat` (if onboarded) or `/onboarding` (if new)
- [ ] `npm run build` passes (0 TypeScript errors)

#### Checklist
- [ ] No `<form>` tags — Clerk components handle their own forms
- [ ] Clerk `<SignIn/SignUp>` wrapped in `bg-card rounded-2xl p-8` card
- [ ] `<RavenbaseLockup />` above Clerk component, `text-primary`
- [ ] Light mode only on auth pages (no `.dark` on `<html>`)
- [ ] `middleware.ts` uses ` clerkMiddleware()` from `@clerk/nextjs/middleware`
- [ ] `apiFetch`: `await auth().getToken()` — not hardcoded
- [ ] `useApiFetch`: `useAuth()` hook — for client components
- [ ] `middleware.ts` redirect: `/` for public, `/login` for dashboard routes

#### Testing
```bash
# Manual test:
# 1. Navigate to http://localhost:3000/login
# 2. Verify: warm cream background, RavenbaseLockup, Clerk SignIn in card
# 3. Sign in with test account
# 4. Verify: redirect to /dashboard (if onboarded) or /onboarding (if new)

# Middleware test:
# 1. Clear cookies/session
# 2. Navigate to http://localhost:3000/graph
# 3. Verify: redirected to /login

npm run build
# Expected: 0 TypeScript errors
```

---

### SUBCOMP-05C: Onboarding Wizard + Profile Switching

**Stories:** STORY-019, STORY-020
**Files:** `app/(auth)/onboarding/page.tsx`, `components/domain/OnboardingWizard.tsx`, `components/domain/ProfileSwitcher.tsx`, `components/domain/Omnibar.tsx`

#### Details
The Onboarding Wizard guides new users through profile creation and their first file upload. Profile Switching allows users to switch between System Profiles via the Omnibar `/profile` command. All API calls are scoped to the active `profile_id` in the request context.

#### Criteria of Done (STORY-019)
- [ ] New user redirected to `/onboarding` after first login
- [ ] Onboarding shows: welcome message, profile name input, optional file upload
- [ ] Profile name required, minimum 2 characters
- [ ] Onboarding creates first System Profile in PostgreSQL
- [ ] Optional file upload triggers ingestion flow
- [ ] Completion redirects to `/chat` (NOT `/dashboard` — see BUG-005)
- [ ] Onboarding shows skip option for file upload

#### Criteria of Done (STORY-020)
- [ ] Omnibar `/profile` command shows profile switcher dropdown
- [ ] Profile list shows all user profiles with active indicator
- [ ] Switching profile updates active profile context
- [ ] All subsequent API calls use new `profile_id` (stored in context/middleware)
- [ ] Profile persisted to localStorage for non-authenticated contexts
- [ ] `profile_id` passed in request header or context for all data calls

#### Checklist (STORY-019)
- [ ] `OnboardingWizard` component with controlled inputs (no `<form>` tags)
- [ ] Profile name: controlled input with validation on blur
- [ ] File upload: `react-dropzone` for drag-and-drop or click-to-upload
- [ ] Calls `POST /v1/profiles` to create profile
- [ ] Calls `POST /v1/ingest/upload` for optional file
- [ ] Redirects to `/dashboard` after completion
- [ ] Skip button for file upload step
- [ ] Loading state during profile creation

#### Checklist (STORY-020)
- [ ] `/profile` command in Omnibar: regex match `/\/profile\b/`
- [ ] `ProfileSwitcher` dropdown: lists all profiles, highlights active
- [ ] Click profile → calls `POST /v1/profiles/switch` or updates local state
- [ ] Active profile stored in React context (`ProfileContext`)
- [ ] `profile_id` included in all data-fetching API calls
- [ ] `useQuery` calls include `profile_id` in query key for cache invalidation
- [ ] Mobile: bottom sheet instead of dropdown

#### Testing
```bash
# Onboarding test:
# 1. Create new Clerk account
# 2. Verify: redirect to /onboarding
# 3. Enter profile name "Work"
# 4. Optionally upload first file
# 5. Verify: redirected to /dashboard
# 6. psql: SELECT * FROM system_profiles WHERE tenant_id = 'user_id'

# Profile switching test:
# 1. Create second profile "Personal"
# 2. Type /profile in Omnibar
# 3. Verify: dropdown shows "Work" (active) and "Personal"
# 4. Click "Personal"
# 5. Verify: active indicator moves to "Personal"
# 6. Upload file → verify goes to "Personal" profile

npm run build
```
