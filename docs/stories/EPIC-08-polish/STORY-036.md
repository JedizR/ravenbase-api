# STORY-036: Internal Admin Dashboard

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium (cross-repo: backend endpoints + frontend pages)
**Depends on:** STORY-023 (credits system), STORY-018 (auth pattern)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — internal admin dashboard story.

## Component
Admin

---

> **Before You Start — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (3-layer pattern, `require_user`, lazy imports, structlog)
> 2. `docs/architecture/03-api-contract.md` — all 5 admin endpoint specs (the `/v1/admin/` section)
> 3. `docs/architecture/02-database-schema.md` — User model (credits_balance, is_active, tier)
> 4. `docs/stories/EPIC-08-polish/STORY-023.md` — CreditTransaction patterns (`admin_adjustment` type)
> 5. `docs/design/CLAUDE_FRONTEND.md` — all 19 frontend rules (frontend session only)
>
> **Session routing:** This is a cross-repo story.
> **In the backend session:** Use the "Backend Agent Brief" at the bottom.
> **In the frontend session:** Use the "Frontend Agent Brief" at the bottom.
> ⚠️ Backend must be deployed and all 5 endpoints verified before the frontend session begins.

---

## User Story
As a founder/admin, I want an internal dashboard where I can view user accounts, adjust
credits manually, and see platform-level metrics — without needing to run raw SQL
against production PostgreSQL.

## Context
- Auth: `ADMIN_USER_IDS` env var — comma-separated Clerk user IDs (set in Railway + `.env.dev`)
- Backend: 5 new endpoints under `/v1/admin/` prefix, protected by `require_admin` dependency
- Frontend: `app/(admin)/` route group in ravenbase-web, verified by middleware
- No Clerk Organizations setup needed — just one env var

## Acceptance Criteria

### Backend
- [x] AC-1: `require_admin` FastAPI dependency: checks `user["user_id"] in settings.admin_user_ids.split(",")`. Returns `403` for authenticated non-admins. `ADMIN_USER_IDS` env var is required (empty = no admin access).
- [x] AC-2: `GET /v1/admin/users?search=&page=&limit=` returns paginated user list with search by email prefix
- [x] AC-3: `GET /v1/admin/users/{user_id}` returns user detail + last 20 credit transactions + source count
- [x] AC-4: `POST /v1/admin/credits/adjust` adds/removes credits, creates `CreditTransaction` with `type="admin_adjustment"` and `description` (audit trail for support)
- [x] AC-5: `POST /v1/admin/users/{user_id}/toggle-active` sets `User.is_active = True/False`
- [x] AC-6: `GET /v1/admin/stats` returns platform metrics including `daily_llm_spend_usd` from Redis circuit breaker key

### Frontend
- [ ] AC-7: `/admin` route group protected by middleware: if user's Clerk ID not in `ADMIN_USER_IDS`, redirect to `/dashboard`
- [ ] AC-8: `/admin` — Stats page: total users, DAU, new today, Pro users, daily LLM spend vs cap (progress bar), sources today, metadocs today
- [ ] AC-9: `/admin/users` — User list with search input (calls `GET /v1/admin/users?search=`), sortable table showing email, tier badge, credit balance, active status, join date
- [ ] AC-10: `/admin/users/[id]` — User detail page: user info + credit transaction history table + "Adjust Credits" form (amount + reason, positive to add, negative to remove) + ban/unban toggle button
- [ ] AC-11: Credit adjustment form: validates `amount` is a non-zero integer, `reason` is required (min 10 chars), shows `toast.success("Credits adjusted")` on success with new balance
- [ ] AC-12: Admin UI uses the existing Ravenbase design system (forest green, shadcn/ui, mono labels for system data). Admin pages have a red `◆ ADMIN_PANEL` mono label in the header to make it visually distinct from the user-facing dashboard.

## Technical Notes

### Files to Create (Backend)
- `src/api/routes/admin.py` — all 5 admin endpoints
- `src/api/dependencies/admin.py` — `require_admin` dependency

### Files to Modify (Backend)
- `src/api/main.py` — register `admin_router` under `/v1/admin/` prefix

### Files to Create (Frontend)
- `app/(admin)/layout.tsx` — admin auth check + admin header with `◆ ADMIN_PANEL`
- `app/(admin)/page.tsx` — stats dashboard
- `app/(admin)/users/page.tsx` — user list
- `app/(admin)/users/[id]/page.tsx` — user detail + credit adjustment

### require_admin Dependency Pattern

```python
# src/api/dependencies/admin.py

from src.api.dependencies.auth import require_user
from src.core.config import settings

async def require_admin(user: dict = Depends(require_user)) -> dict:
    """Extend require_user to verify admin access."""
    admin_ids = [uid.strip() for uid in settings.ADMIN_USER_IDS.split(",") if uid.strip()]
    if not admin_ids or user["user_id"] not in admin_ids:
        raise HTTPException(
            status_code=403,
            detail={"code": "ADMIN_REQUIRED", "message": "Admin access required"}
        )
    return user
```

### Admin Middleware Pattern (Frontend)

```tsx
// app/(admin)/layout.tsx
import { auth } from "@clerk/nextjs/server"
import { redirect } from "next/navigation"

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const { userId } = await auth()
  const adminIds = (process.env.ADMIN_USER_IDS || "").split(",").map(id => id.trim())

  if (!userId || !adminIds.includes(userId)) {
    redirect("/dashboard")  // Non-admins go to their dashboard silently
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-6 py-4 flex items-center gap-4">
        <RavenbaseLockup size="sm" />
        <span className="font-mono text-xs text-destructive tracking-wider">
          ◆ ADMIN_PANEL
        </span>
      </header>
      <main>{children}</main>
    </div>
  )
}
```

### Architecture Constraints
- `require_admin` always calls `require_user` first — never bypasses JWT validation
- Admin endpoints are read/write; keep mutations simple (adjust balance, toggle active)
- Never expose other users' passwords, Clerk internal tokens, or payment instrument details
- Credit adjustments always create a CreditTransaction record — no silent balance changes
- `ADMIN_USER_IDS` env var must not be committed to the repo (add to `.gitignore` and `.env.example`)

## Definition of Done
- [ ] `require_admin` returns `403` for non-admin authenticated users
- [ ] All 5 admin API endpoints work and are protected
- [ ] Admin UI accessible only to users in `ADMIN_USER_IDS`
- [ ] Credit adjustment creates audit CreditTransaction
- [ ] Stats page shows real data including daily LLM spend
- [ ] `make quality && make test` passes (backend)
- [ ] `npm run build` passes (frontend)

## Testing This Story

```bash
# Backend:
# 1. Set ADMIN_USER_IDS=your_clerk_user_id in .env.dev
# 2. Test GET /v1/admin/stats — should return platform metrics
# 3. Adjust credits for test user, verify CreditTransaction created
# 4. Test with non-admin JWT — should get 403

# Frontend:
# 1. Log in as admin user → navigate to /admin → see stats dashboard
# 2. Log in as non-admin → navigate to /admin → should redirect to /dashboard
```

---

## Backend Agent Brief

```
Implement STORY-036 backend: Admin API endpoints.

Read first:
1. CLAUDE.md (architecture rules — 3-layer, require_user pattern in auth.py)
2. docs/architecture/03-api-contract.md (all 5 admin endpoint specs)
3. docs/stories/EPIC-08-polish/STORY-036.md (this file, backend ACs 1-6)

Key:
- require_admin extends require_user — never bypass JWT validation
- Credit adjustment MUST create CreditTransaction record (audit trail)
- admin/stats reads llm:daily_spend:{today} from Redis

Show plan first. Do not implement yet.
```

---

## Frontend Agent Brief

```
Implement STORY-036 frontend: Admin Dashboard UI.
Complete ONLY after backend STORY-036 endpoints are deployed and tested.

Read first:
1. CLAUDE.md (for CLAUDE_FRONTEND.md — all 19 rules)
2. docs/design/01-design-system.md (design tokens, shadcn/ui components)
3. docs/architecture/03-api-contract.md (admin endpoint shapes)
4. docs/stories/EPIC-08-polish/STORY-036.md (this file, frontend ACs 7-12)

Key:
- Admin layout must redirect non-admins to /dashboard silently
- Use shadcn/ui Table for user list, shadcn/ui Card for stats
- ◆ ADMIN_PANEL mono label in header (text-destructive red, not green)
- Credit adjustment: validate amount non-zero, reason min 10 chars

Show plan first. Do not implement yet.
```

---

## Development Loop
Follow `docs/DEVELOPMENT_LOOP.md`.
```bash
# Backend:
make quality && make test
git commit -m "feat(ravenbase): STORY-036 admin API endpoints"

# Frontend:
npm run build && npm run test
git commit -m "feat(ravenbase): STORY-036 admin dashboard frontend"
```
