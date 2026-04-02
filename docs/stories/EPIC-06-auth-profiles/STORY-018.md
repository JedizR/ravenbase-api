# STORY-018: Clerk Auth Integration (Frontend + Backend Webhook)

**Epic:** EPIC-06 — Authentication & System Profiles
**Priority:** P0
**Complexity:** Medium
**Depends on:** STORY-001

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-09-AC-1: Every protected endpoint validates JWT via require_user dependency
- FR-09-AC-2: tenant_id = JWT sub claim — never from body or query
- FR-09-AC-3: Expired tokens return 403 TOKEN_EXPIRED
- FR-09-AC-4: Invalid tokens return 403 INVALID_TOKEN
- FR-09-AC-5: SSE endpoints use verify_token_query_param (JWT in ?token= query param)
- FR-09-AC-6: Clerk webhook creates User record in PostgreSQL on first sign-up

## Component
COMP-05: AuthSystem

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (no form tags, apiFetch pattern)
> 3. `docs/architecture/05-security-privacy.md` — Clerk JWT validation pattern, CORS config
> 4. `docs/architecture/02-database-schema.md` — User model (to create on webhook)
> 5. `docs/architecture/03-api-contract.md` — webhook endpoint spec

> **This story spans BOTH repos. Always work backend first:**
>
> **Part 1 — Backend** (`ravenbase-api/`): `require_user` dependency + webhook handler
> → Complete Part 1 first. Merge it. Verify JWT enforcement before moving to frontend.
>
> **Part 2 — Frontend** (`ravenbase-web/`): SignIn/SignUp pages + middleware + apiFetch
> → Only start Part 2 after Part 1 backend auth is confirmed working.
>
> **In the backend session:** Use the "Backend Agent Brief" at the bottom of this story.
> **In the frontend session:** Use the "Frontend Agent Brief" at the bottom of this story.

---

## User Story
As a new user, I want to register with email and immediately access the platform.

## Context
- Auth pattern: `architecture/05-security-privacy.md` — `require_user` implementation with Clerk JWT
- User model: `architecture/02-database-schema.md` — `users` table
- API contract: `architecture/03-api-contract.md` — `/webhooks/clerk` and `/webhooks/stripe` endpoints
- Frontend rules: `design/CLAUDE_FRONTEND.md` — `apiFetch()` pattern for attaching JWT

## Acceptance Criteria
- [ ] AC-1: Frontend: Clerk `<SignIn>` and `<SignUp>` components at `/login` and `/register`
- [ ] AC-2: Backend: `require_user` dependency validates Clerk JWT correctly in all protected endpoints
- [ ] AC-3: Clerk webhook: `POST /webhooks/clerk` creates a `User` record in PostgreSQL on `user.created` event
- [ ] AC-4: Webhook signature validated using `svix` library (prevent fake webhook requests)
- [ ] AC-5: After login: redirect to `/dashboard` if user has completed onboarding, else `/onboarding`
- [ ] AC-6: Auth middleware on all dashboard routes (redirect to `/login` if unauthenticated)
- [ ] AC-7: JWT token from Clerk attached to all API requests via `apiFetch` wrapper

## Technical Notes

### Files to Create (Frontend)
- `app/(auth)/login/page.tsx` — `<SignIn />` from `@clerk/nextjs`
- `app/(auth)/register/page.tsx` — `<SignUp />` from `@clerk/nextjs`
- `lib/api.ts` — `apiFetch<T>()` wrapper attaching Clerk Bearer token to all requests
- `middleware.ts` — protect all `/dashboard/*` routes (redirect to `/login` if unauthenticated)

### Files to Create (Backend)
- `src/api/dependencies/auth.py` — complete `require_user(authorization: str | None = Header(None))`
- `src/api/routes/webhooks.py` — `POST /webhooks/clerk` validates svix signature, creates User on `user.created`; `POST /webhooks/stripe` handles `checkout.session.completed`

### Architecture Constraints
- `svix` must validate webhook signatures — never process unsigned webhook payloads
- `require_user` must raise `401` for missing auth header, `403` for invalid/expired token
- `apiFetch` must retrieve the Clerk token with `await auth().getToken()` — never hardcode tokens
- The `User.id` in PostgreSQL must equal the Clerk `user_id` (set during `user.created` webhook)
- Auth pages (`(auth)/`) are light mode and do NOT require auth

### Webhook Security Pattern
```python
# src/api/routes/webhooks.py
from svix.webhooks import Webhook, WebhookVerificationError

@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request):
    raw_body = await request.body()
    headers = dict(request.headers)
    wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
    try:
        payload = wh.verify(raw_body, headers)
    except WebhookVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if payload["type"] == "user.created":
        user_data = payload["data"]
        # Create User in PostgreSQL with id = user_data["id"]
        ...
```

### apiFetch Pattern
```typescript
// lib/api.ts
import { auth } from "@clerk/nextjs/server";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { getToken } = auth();
  const token = await getToken();
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.message ?? "API error");
  }
  return response.json() as Promise<T>;
}
```

## Definition of Done
- [ ] New user can register, log in, and reach `/dashboard`
- [ ] JWT validated on `GET /v1/graph/nodes` (returns 403 without token)
- [ ] Clerk webhook creates User in PostgreSQL (verify via psql: `SELECT * FROM users`)
- [ ] `make quality` passes (0 errors)
- [ ] `npm run build` passes (0 TypeScript errors)

## Testing This Story

```bash
# Backend: verify JWT enforcement
curl -X GET http://localhost:8000/v1/graph/nodes
# Expected: 401 Unauthorized

# Backend: verify with valid token
curl -X GET http://localhost:8000/v1/graph/nodes \
  -H "Authorization: Bearer YOUR_CLERK_JWT"
# Expected: 200 {"nodes": [], "edges": []}

# Backend: test webhook locally with Clerk CLI
# → Use ngrok or Clerk's local webhook forwarding
# → Create a test user → check DB: SELECT * FROM users WHERE email='test@example.com'

# Quality check
make quality
npm run build
```

**Passing result:** New user registers, Clerk `user.created` fires, User row appears in PostgreSQL `users` table. All `/v1/*` endpoints return 401 without a valid JWT.

---

## Backend Agent Brief (for ravenbase-api/ session)

```
Implement STORY-018 Part 1 (Backend): Clerk auth integration.
This is the backend half only. Do NOT implement frontend pages.

Read first:
1. CLAUDE.md (architecture rules)
2. docs/architecture/05-security-privacy.md (require_user + webhook validation patterns)
3. docs/architecture/02-database-schema.md (User model)
4. docs/stories/EPIC-06-auth-profiles/STORY-018.md (this file)

Backend constraints:
- require_user uses PyJWT + Clerk JWKS endpoint for validation (NOT the clerk-backend-api SDK)
- JWKS client is module-level cached (_get_jwks_client()) — not created per request
- Required env var: CLERK_FRONTEND_API (your Clerk frontend API domain)
- Raises 401 for missing auth header, 403 for expired/invalid token
- svix validates webhook signature — reject unsigned requests with 400
- User.id MUST equal Clerk user_id
- Use KICKSTART.md Clerk CLI instructions for local webhook testing

Show plan first. Do not implement yet.
```

## Frontend Agent Brief (for ravenbase-web/ session)

```
Implement STORY-018 Part 2 — Frontend: Clerk auth pages + middleware.
Part 1 (backend) was completed in Phase A as STORY-018-BE and is
already merged to ravenbase-api main.

Read these files FIRST — in this exact order — before planning:
1. CLAUDE.md (repo root — all 19 frontend rules)
2. docs/design/AGENT_DESIGN_PREAMBLE.md (NON-NEGOTIABLE — read fully)
3. docs/design/00-brand-identity.md (logo spec, voice, mono labels)
4. docs/design/01-design-system.md (all color tokens and typography)
5. docs/stories/EPIC-06-auth-profiles/STORY-018.md (this file)

What to build:
- app/(auth)/login/page.tsx — Clerk <SignIn /> with Ravenbase branding
- app/(auth)/register/page.tsx — Clerk <SignUp /> with Ravenbase branding
- app/(auth)/layout.tsx — light mode, centered, cream background
- lib/api.ts — apiFetch<T>() for Server Components
- lib/api-client.ts — useApiFetch() hook for Client Components
- middleware.ts — protect all /dashboard/* routes via clerkMiddleware()
- components/brand/RavenbaseLogo.tsx — SVG mark (spec in 00-brand-identity.md)
- components/brand/RavenbaseLockup.tsx — mark + wordmark
- components/brand/index.ts — re-exports

Constraints:
- No <form> tags anywhere (RULE 1)
- Auth pages: warm cream background, RavenbaseLockup centered above
  the Clerk component, light mode only
- Clerk <SignIn /> and <SignUp /> appear inside a bg-card rounded-2xl
  shadow-sm card — not floating on a blank page
- After login: redirect to /dashboard (no onboarding check yet —
  that is STORY-019's responsibility)
- middleware.ts protects /dashboard/* and redirects to /login
- story-counter.txt is already 018-FE
- Journal entry goes under a NEW ## Sprint 20 section (**Sprint:** 20)
- story-counter after completion: 019

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
git add -A && git commit -m "feat(ravenbase): STORY-018 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-018"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-018
git add docs/stories/epics.md && git commit -m "docs: mark STORY-018 complete"
```
