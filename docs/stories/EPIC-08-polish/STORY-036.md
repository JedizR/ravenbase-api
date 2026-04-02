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
- `app/(admin)/loading.tsx` — stats page loading skeleton
- `app/(admin)/users/loading.tsx` — user list loading skeleton

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

## UX & Visual Quality Requirements

### Admin Dashboard Visual Design
1. Admin dashboard MUST feel like an internal tool, not a public product.
   All standard design system rules apply (forest green, cream bg, rounded-2xl cards).

2. Stat cards row at top (4 cards):
   - Total users / Active this week / Total credits used / Revenue this month
   - bg-card rounded-2xl border border-border p-6
   - Large number: font-mono text-3xl font-bold text-foreground
   - Label: text-xs font-mono text-muted-foreground tracking-wider below
   - Trend indicator: green ▲ or red ▼ with percentage vs last week
   - Card hover: hover:shadow-md transition-shadow

3. User management table:
   - Table header: bg-secondary/50 rounded-t-xl font-mono text-xs text-muted-foreground uppercase
   - Row hover: bg-secondary/30 transition-colors cursor-pointer
   - Each row shows: Avatar (Clerk imageUrl or initials fallback) | Email |
     Tier badge | Credits | Last active | Actions menu
   - Tier badges: Free=bg-secondary, Pro=bg-primary/10 text-primary,
     Team=bg-accent/30 text-foreground
   - Pagination: "Showing X-Y of Z" with Prev/Next buttons

4. Actions dropdown per user row:
   - Three-dot menu (MoreHorizontal icon) that opens a DropdownMenu
   - Options: View details | Adjust credits | Change tier | Disable account
   - Each option has an appropriate Lucide icon
   - Destructive action (Disable): text-destructive
   - Dropdown animation: scale(0.95)→scale(1) fade-in 150ms

5. Credit adjustment dialog:
   - Triggered from Actions → Adjust credits
   - Uses shadcn Dialog component
   - Shows current balance
   - +/- stepper buttons: increment/decrement by 100
   - Or direct input field for exact amount
   - Reason textarea (required, min 10 chars)
   - Submit button: rounded-full bg-primary (only enabled when reason filled)

6. Search/filter bar above table:
   - bg-secondary rounded-xl px-4 py-2 flex items-center gap-2
   - Search icon: text-muted-foreground
   - Input: bg-transparent outline-none text-sm placeholder:text-muted-foreground
   - Filter pills: Tier (All/Free/Pro/Team) and Status (All/Active/Disabled)
   - Each pill: rounded-full text-xs font-mono px-3 py-1
   - Active pill: bg-primary text-primary-foreground
   - Inactive pill: bg-secondary text-muted-foreground hover:bg-secondary/80

## Definition of Done
- [ ] `require_admin` returns `403` for non-admin authenticated users
- [ ] All 5 admin API endpoints work and are protected
- [ ] Admin UI accessible only to users in `ADMIN_USER_IDS`
- [ ] Credit adjustment creates audit CreditTransaction
- [ ] Stats page shows real data including daily LLM spend
- [ ] `make quality && make test` passes (backend)
- [ ] `npm run build` passes (frontend)

## Final Localhost Verification (mandatory before marking complete)

After `make quality && make test` (backend) and `npm run build` (frontend) pass, verify the running application works:

**Step 1 — Start backend dev server:**
```bash
cd ravenbase-api && make run
```

**Step 2 — Clear frontend cache and start dev server:**
```bash
rm -rf .next && npm run dev
```

**Step 3 — Verify no runtime errors:**
- Open http://localhost:3000 in the browser
- Log in as admin user, navigate to `/admin`
- Confirm NO "Internal Server Error" or webpack runtime errors
- Confirm CSS loads correctly (no unstyled content)
- Open browser DevTools → Console tab
- Confirm no red errors (yellow warnings acceptable)

**Step 4 — Report one of:**
- ✅ `localhost verified` — admin dashboard renders correctly
- ⚠️ `Issue found: [describe issue]` — fix before committing docs

Only commit the docs update (epics.md, story-counter, project-status, journal) AFTER localhost verification passes.

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

> **Skill Invocations — invoke each skill before the corresponding phase:**
>
> **Phase 1 (Read/Design):** `Use /frontend-design — enforce production-grade aesthetic compliance`
> **Phase 2 (Admin Layout):** `Use /tailwindcss — for Tailwind CSS v4 token system`
> **Phase 3 (Stats Page):** `Use /tailwindcss-advanced-layouts — for admin dashboard layout`
> **Phase 4 (User Management):** `Use /tailwindcss — for table and form components`
> **Phase 5 (User Detail):** `Use /tailwindcss — for user detail page + credit adjustment`
> **Phase 6 (Accessibility):** `Use /tailwindcss-animations — for micro-interaction verification`
> **Phase 7 (Verification):** `Use /superpowers:verification-before-completion — before claiming done`

---

```
🎯 Target: Claude Code / MiniMax-M2.7 — Ultra-detailed planning and implementation
💡 Optimization: MiniMax-M2.7 directive — WRITE EVERYTHING IN MAXIMUM DETAIL.
   Complete code for every component. Complete grep commands for every AC.

═══════════════════════════════════════════════════════════════════
CONTEXT
═══════════════════════════════════════════════════════════════════

This story has a BACKEND PART and a FRONTEND PART.

Backend (AC-1 through AC-6): admin endpoints, user management, credit adjustment.
Frontend (AC-7 through AC-12): Admin Dashboard UI.

Frontend ACs:
- AC-7: Admin layout redirects non-admins to /dashboard
- AC-8: Stats dashboard with 4 cards + LLM spend progress bar
- AC-9: User table with search + tier filter pills + actions dropdown
- AC-10: User detail page: credit transaction history + credit adjustment form + ban/unban toggle
- AC-11: Credit adjustment: amount ≠ 0, reason min 10 chars, toast.success on success
- AC-12: ◆ ADMIN_PANEL in text-destructive (RED), not green

Admin user IDs stored in: ADMIN_USER_IDS env var (comma-separated Clerk IDs).

═══════════════════════════════════════════════════════════════════
READING ORDER
═══════════════════════════════════════════════════════════════════

INVOKE: Use /frontend-design

Read ALL files. Write "✅ CONFIRMED READ: [filename]" after each:

1. CLAUDE.md — all 19 rules
   → Especially:
   - RULE 5: no forced color mode in route groups
   - RULE 6: TanStack Query for server state
   - RULE 10: every dashboard page needs loading.tsx
   - RULE 11: touch targets 44px minimum

2. docs/design/AGENT_DESIGN_PREAMBLE.md
   → Anti-patterns to reject:
     ❌ bg-[#2d4a3e] → bg-primary
     ❌ rounded-lg on cards → rounded-2xl
     ❌ rounded-md on CTAs → rounded-full
     ❌ <form> tag → onClick + controlled inputs

3. docs/design/00-brand-identity.md — mono label ◆ PATTERN, logo usage
4. docs/design/01-design-system.md — brand colors, typography, radius scale
5. docs/design/04-ux-patterns.md — interaction patterns, states, micro-animations
6. docs/stories/EPIC-08-polish/STORY-036.md (this file — all ACs 7-12)

═══════════════════════════════════════════════════════════════════
ADMIN LAYOUT — full code
═══════════════════════════════════════════════════════════════════

FILE: app/(admin)/layout.tsx

"use client"
import { auth } from "@clerk/nextjs/server"
import { redirect } from "next/navigation"
import { RavenbaseLockup } from "@/components/brand"

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const { userId } = await auth()

  // AC-7: redirect non-admins silently to /dashboard
  const adminIds = (process.env.ADMIN_USER_IDS ?? "")
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean)

  if (!userId || !adminIds.includes(userId)) {
    redirect("/dashboard")
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Admin header — forest green left accent bar + ◆ ADMIN_PANEL in RED */}
      <header className="border-b border-border bg-card">
        <div className="flex items-center gap-4 px-6 py-4">
          {/* Red left accent bar */}
          <div className="w-1 h-8 bg-destructive rounded-full" />
          <RavenbaseLockup size="sm" />
          {/* AC-12: ◆ ADMIN_PANEL in text-destructive (RED) */}
          <span className="font-mono text-xs text-destructive tracking-wider font-bold">
            ◆ ADMIN_PANEL
          </span>
        </div>
      </header>
      <main id="main-content">{children}</main>
    </div>
  )
}

═══════════════════════════════════════════════════════════════════
ADMIN STATS PAGE — full code
═══════════════════════════════════════════════════════════════════

FILE: app/(admin)/page.tsx

"use client"
import { useQuery } from "@tanstack/react-query"
import { Users, Zap, CreditCard, DollarSign, Activity, Database, FileText } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { RavenbaseLogo } from "@/components/brand"
import Link from "next/link"

interface AdminStats {
  total_users: number
  active_this_week: number
  new_users_today: number
  pro_users: number
  total_credits_used: number
  revenue_this_month: number
  daily_llm_spend: number
  daily_llm_spend_cap: number
  sources_today: number
  metadocs_today: number
}

export default function AdminDashboardPage() {
  const { data: stats, isLoading } = useQuery<AdminStats>({
    queryKey: ["admin", "stats"],
    queryFn: () => apiFetch<AdminStats>("/v1/admin/stats"),
    staleTime: 30_000,
  })

  const statCards = [
    {
      label: "Total Users",
      value: stats?.total_users ?? 0,
      icon: Users,
      accent: "text-primary",
    },
    {
      label: "Active This Week",
      value: stats?.active_this_week ?? 0,
      icon: Activity,
      accent: "text-success",
    },
    {
      label: "New Today",
      value: stats?.new_users_today ?? 0,
      icon: Zap,
      accent: "text-warning",
    },
    {
      label: "Pro Users",
      value: stats?.pro_users ?? 0,
      icon: DollarSign,
      accent: "text-primary",
    },
    {
      label: "Total Credits Used",
      value: stats?.total_credits_used?.toLocaleString() ?? "—",
      icon: CreditCard,
      accent: "text-muted-foreground",
    },
    {
      label: "Revenue This Month",
      value: stats?.revenue_this_month
        ? `$${stats.revenue_this_month.toLocaleString()}`
        : "—",
      icon: DollarSign,
      accent: "text-success",
    },
  ]

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-56" />
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-2xl" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-8">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-serif text-3xl text-foreground">Platform Overview</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time metrics — refreshes every 30 seconds
          </p>
        </div>
        <Link
          href="/admin/users"
          className="px-5 py-2.5 rounded-full bg-primary text-primary-foreground
                     text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Manage Users →
        </Link>
      </div>

      {/* Stat cards grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((card) => (
          <div
            key={card.label}
            className="bg-card rounded-2xl border border-border p-5
                       hover:shadow-md transition-shadow duration-150"
          >
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-mono text-muted-foreground tracking-wider uppercase">
                {card.label}
              </p>
              <card.icon className={`w-4 h-4 ${card.accent}`} />
            </div>
            <p className="font-mono text-2xl font-bold text-foreground">
              {card.value}
            </p>
          </div>
        ))}
      </div>

      {/* LLM Spend progress bar */}
      {stats && (
        <div className="bg-card rounded-2xl border border-border p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p className="text-xs font-mono text-muted-foreground tracking-wider uppercase">
                Daily LLM Spend
              </p>
            </div>
            <p className="font-mono text-sm text-foreground">
              ${stats.daily_llm_spend.toFixed(4)} / ${stats.daily_llm_spend_cap.toLocaleString()}
            </p>
          </div>
          <div className="h-2.5 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, (stats.daily_llm_spend / stats.daily_llm_spend_cap) * 100)}%`,
              }}
            />
          </div>
          {stats.daily_llm_spend > stats.daily_llm_spend_cap * 0.9 && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-warning">⚠</span>
              <p className="text-xs font-mono text-warning">
                Near daily cap — monitor closely
              </p>
            </div>
          )}
        </div>
      )}

      {/* Activity today */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-card rounded-2xl border border-border p-5 space-y-2">
          <p className="text-xs font-mono text-muted-foreground tracking-wider uppercase">
            Sources Ingested Today
          </p>
          <div className="flex items-center gap-3">
            <Database className="w-5 h-5 text-primary" />
            <span className="font-mono text-2xl font-bold text-foreground">
              {stats?.sources_today ?? "—"}
            </span>
          </div>
        </div>
        <div className="bg-card rounded-2xl border border-border p-5 space-y-2">
          <p className="text-xs font-mono text-muted-foreground tracking-wider uppercase">
            MetaDocs Synthesized Today
          </p>
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-primary" />
            <span className="font-mono text-2xl font-bold text-foreground">
              {stats?.metadocs_today ?? "—"}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

═══════════════════════════════════════════════════════════════════
ADMIN USER LIST PAGE — full code
═══════════════════════════════════════════════════════════════════

FILE: app/(admin)/users/page.tsx

"use client"
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Search, MoreHorizontal, Ban, CheckCircle, Coins, User, ChevronLeft, ChevronRight } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import { Minus, Plus } from "lucide-react"
import Link from "next/link"

interface User {
  id: string
  email: string
  tier: "free" | "pro" | "team"
  credits_balance: number
  is_active: boolean
  created_at: string
}

interface UsersResponse {
  users: User[]
  total: number
  page: number
  limit: number
}

type TierFilter = "All" | "Free" | "Pro" | "Team"
type StatusFilter = "All" | "Active" | "Disabled"

const PAGE_SIZE = 20

export default function AdminUsersPage() {
  const [search, setSearch] = useState("")
  const [tierFilter, setTierFilter] = useState<TierFilter>("All")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All")
  const [page, setPage] = useState(1)
  const [creditDialogUser, setCreditDialogUser] = useState<User | null>(null)
  const [adjustAmount, setAdjustAmount] = useState(0)
  const [reason, setReason] = useState("")
  const queryClient = useQueryClient()

  const { data: resp, isLoading } = useQuery<UsersResponse>({
    queryKey: ["admin", "users", search, tierFilter, statusFilter, page],
    queryFn: () => {
      const params = new URLSearchParams({
        search: search || "",
        tier: tierFilter === "All" ? "" : tierFilter.toLowerCase(),
        is_active: statusFilter === "Active" ? "true" : statusFilter === "Disabled" ? "false" : "",
        page: String(page),
        limit: String(PAGE_SIZE),
      })
      return apiFetch<UsersResponse>(`/v1/admin/users?${params}`)
    },
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  })

  const adjustMutation = useMutation({
    mutationFn: (payload: { user_id: string; amount: number; reason: string }) =>
      apiFetch<{ new_balance: number }>("/v1/admin/credits/adjust", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (data, { user_id }) => {
      toast.success(`Credits adjusted. New balance: ${data.new_balance.toLocaleString()}`)
      setCreditDialogUser(null)
      setAdjustAmount(0)
      setReason("")
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
    },
    onError: () => {
      toast.error("Failed to adjust credits. Please try again.")
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: (payload: { user_id: string; is_active: boolean }) =>
      apiFetch("/v1/admin/users/toggle-active", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (_, { is_active }) => {
      toast.success(is_active ? "User enabled" : "User disabled")
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
    },
    onError: () => {
      toast.error("Failed to update user status.")
    },
  })

  const tierBadgeClass = (tier: string) => {
    if (tier === "pro") return "bg-primary/10 text-primary"
    if (tier === "team") return "bg-accent/30 text-foreground"
    return "bg-secondary text-muted-foreground"
  }

  const tierPillClass = (t: TierFilter) =>
    tierPillClass: (t: TierFilter) =>
      tierPillClass(t === tierFilter
        ? "bg-primary text-primary-foreground"
        : "bg-secondary text-muted-foreground hover:bg-secondary/80")

  const statusPillClass = (s: StatusFilter) =>
    statusPillClass: (s: StatusFilter) =>
      statusPillClass(s === statusFilter
        ? "bg-primary text-primary-foreground"
        : "bg-secondary text-muted-foreground hover:bg-secondary/80")

  const users = resp?.users ?? []
  const total = resp?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const startItem = (page - 1) * PAGE_SIZE + 1
  const endItem = Math.min(page * PAGE_SIZE, total)

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="font-serif text-3xl text-foreground">User Management</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {total.toLocaleString()} total users
        </p>
      </div>

      {/* Search + filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search input */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder="Search by email..."
            className="w-full bg-secondary rounded-xl pl-10 pr-4 py-2.5
                       text-sm text-foreground outline-none border border-border
                       placeholder:text-muted-foreground
                       focus:ring-2 focus:ring-primary/30 focus:border-primary"
          />
        </div>
        {/* Tier filter pills */}
        <div className="flex gap-1.5">
          {(["All", "Free", "Pro", "Team"] as TierFilter[]).map((tier) => (
            <button
              key={tier}
              onClick={() => { setTierFilter(tier); setPage(1) }}
              className={`px-3 py-1.5 rounded-full text-xs font-mono transition-colors min-h-[36px] ${tierPillClass(tier)}`}
            >
              {tier}
            </button>
          ))}
        </div>
        {/* Status filter pills */}
        <div className="flex gap-1.5">
          {(["All", "Active", "Disabled"] as StatusFilter[]).map((status) => (
            <button
              key={status}
              onClick={() => { setStatusFilter(status); setPage(1) }}
              className={`px-3 py-1.5 rounded-full text-xs font-mono transition-colors min-h-[36px] ${statusPillClass(status)}`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* User table */}
      <div className="bg-card rounded-2xl border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-secondary/50 hover:bg-secondary/50">
              <TableHead className="font-mono text-xs uppercase w-[280px] pl-5">
                User
              </TableHead>
              <TableHead className="font-mono text-xs uppercase">Tier</TableHead>
              <TableHead className="font-mono text-xs uppercase">Credits</TableHead>
              <TableHead className="font-mono text-xs uppercase">Status</TableHead>
              <TableHead className="font-mono text-xs uppercase">Joined</TableHead>
              <TableHead className="w-12 pr-3" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell className="pl-5"><Skeleton className="h-5 w-48" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-12" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-8 w-8" /></TableCell>
                  </TableRow>
                ))
              : users.map((user) => (
                  <TableRow
                    key={user.id}
                    className="hover:bg-secondary/30 transition-colors cursor-pointer"
                  >
                    <TableCell className="pl-5">
                      <Link href={`/admin/users/${user.id}`} className="flex items-center gap-3">
                        <Avatar className="w-8 h-8">
                          <AvatarFallback className="text-xs bg-secondary">
                            {user.email[0].toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <span className="text-sm text-foreground hover:text-primary">
                          {user.email}
                        </span>
                      </Link>
                    </TableCell>
                    <TableCell>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-mono ${tierBadgeClass(user.tier)}`}>
                        {user.tier.toUpperCase()}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-sm text-foreground">
                      {user.credits_balance.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <span className={`
                        px-2 py-0.5 rounded-full text-xs font-mono
                        ${user.is_active
                          ? "bg-success/10 text-success"
                          : "bg-destructive/10 text-destructive"
                        }
                      `}>
                        {user.is_active ? "ACTIVE" : "DISABLED"}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(user.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="pr-3">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="w-8 h-8 text-muted-foreground hover:text-foreground"
                          >
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="rounded-xl min-w-[180px]">
                          <DropdownMenuItem asChild>
                            <Link href={`/admin/users/${user.id}`} className="flex items-center">
                              <User className="w-4 h-4 mr-2" /> View details
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setCreditDialogUser(user)}>
                            <Coins className="w-4 h-4 mr-2" /> Adjust credits
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() =>
                              toggleActiveMutation.mutate({
                                user_id: user.id,
                                is_active: !user.is_active,
                              })
                            }
                            className={!user.is_active ? "text-success focus:text-success" : "text-destructive focus:text-destructive"}
                          >
                            {user.is_active ? (
                              <><Ban className="w-4 h-4 mr-2" /> Disable account</>
                            ) : (
                              <><CheckCircle className="w-4 h-4 mr-2" /> Enable account</>
                            )}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-4 border-t border-border">
            <p className="text-xs font-mono text-muted-foreground">
              Showing {startItem}–{endItem} of {total.toLocaleString()}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                className="w-8 h-8"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-xs font-mono text-foreground px-2">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="icon"
                className="w-8 h-8"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Credit Adjustment Dialog */}
      <Dialog
        open={!!creditDialogUser}
        onOpenChange={(o) => {
          if (!o) {
            setCreditDialogUser(null)
            setAdjustAmount(0)
            setReason("")
          }
        }}
      >
        <DialogContent className="rounded-2xl max-w-sm">
          <DialogHeader>
            <DialogTitle>Adjust Credits</DialogTitle>
            <DialogDescription className="text-xs font-mono text-muted-foreground">
              {creditDialogUser?.email}
            </DialogDescription>
          </DialogHeader>

          {/* Current balance display */}
          <div className="bg-secondary/50 rounded-xl px-4 py-3 text-center">
            <p className="text-xs font-mono text-muted-foreground mb-1">Current Balance</p>
            <p className="font-mono text-2xl font-bold text-foreground">
              {creditDialogUser?.credits_balance.toLocaleString()}
            </p>
          </div>

          {/* Stepper */}
          <div className="flex items-center justify-center gap-4">
            <Button
              variant="outline"
              size="icon"
              className="w-10 h-10 rounded-full"
              onClick={() => setAdjustAmount((a) => a - 100)}
            >
              <Minus className="w-4 h-4" />
            </Button>
            <input
              type="number"
              value={adjustAmount}
              onChange={(e) => setAdjustAmount(parseInt(e.target.value) || 0)}
              className="w-28 text-center font-mono text-2xl font-bold border border-border
                         rounded-xl px-3 py-2 outline-none bg-card
                         focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
            <Button
              variant="outline"
              size="icon"
              className="w-10 h-10 rounded-full"
              onClick={() => setAdjustAmount((a) => a + 100)}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>

          {/* New balance preview */}
          {adjustAmount !== 0 && (
            <p className="text-center text-xs font-mono text-muted-foreground">
              New balance:{" "}
              <span className={adjustAmount > 0 ? "text-success" : "text-destructive"}>
                {(creditDialogUser?.credits_balance ?? 0) + adjustAmount}.toLocaleString()
              </span>
            </p>
          )}

          {/* Reason textarea */}
          <div className="space-y-1.5">
            <label htmlFor="adjust-reason" className="text-sm font-medium text-foreground">
              Reason <span className="text-destructive">*</span>
            </label>
            <textarea
              id="adjust-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Describe why you are adjusting credits (min 10 characters)..."
              rows={3}
              className="w-full rounded-xl border border-border px-3 py-2.5 text-sm
                         outline-none bg-card resize-none
                         focus:ring-2 focus:ring-primary/30 focus:border-primary
                         placeholder:text-muted-foreground"
            />
            {reason.length > 0 && reason.length < 10 && (
              <p className="text-xs text-destructive">
                {10 - reason.length} more characters required
              </p>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setCreditDialogUser(null)
                setAdjustAmount(0)
                setReason("")
              }}
              className="rounded-full"
            >
              Cancel
            </Button>
            <Button
              onClick={() =>
                creditDialogUser &&
                adjustMutation.mutate({
                  user_id: creditDialogUser.id,
                  amount: adjustAmount,
                  reason,
                })
              }
              disabled={adjustAmount === 0 || reason.length < 10}
              className="rounded-full bg-primary text-primary-foreground
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {adjustAmount > 0
                ? `Add ${adjustAmount} credits`
                : adjustAmount < 0
                ? `Remove ${Math.abs(adjustAmount)} credits`
                : "Set amount"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

═══════════════════════════════════════════════════════════════════
ADMIN USER DETAIL PAGE — full code
═══════════════════════════════════════════════════════════════════

FILE: app/(admin)/users/[id]/page.tsx

"use client"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useParams } from "next/navigation"
import { Ban, CheckCircle, Coins, ArrowLeft, CreditCard } from "lucide-react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import { useState } from "react"
import { Minus, Plus } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

interface CreditTransaction {
  id: string
  type: string
  amount: number
  balance_after: number
  description: string
  created_at: string
}

interface UserDetail {
  id: string
  email: string
  tier: "free" | "pro" | "team"
  credits_balance: number
  is_active: boolean
  created_at: string
  last_active_at: string | null
  sources_count: number
  credit_transactions: CreditTransaction[]
}

export default function AdminUserDetailPage() {
  const params = useParams()
  const userId = params.id as string
  const queryClient = useQueryClient()

  const [creditDialogOpen, setCreditDialogOpen] = useState(false)
  const [banDialogOpen, setBanDialogOpen] = useState(false)
  const [adjustAmount, setAdjustAmount] = useState(0)
  const [reason, setReason] = useState("")

  const { data: user, isLoading } = useQuery<UserDetail>({
    queryKey: ["admin", "user", userId],
    queryFn: () => apiFetch<UserDetail>(`/v1/admin/users/${userId}`),
    staleTime: 30_000,
  })

  const adjustMutation = useMutation({
    mutationFn: (payload: { user_id: string; amount: number; reason: string }) =>
      apiFetch<{ new_balance: number }>("/v1/admin/credits/adjust", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (data) => {
      toast.success(`Credits adjusted. New balance: ${data.new_balance.toLocaleString()}`)
      setCreditDialogOpen(false)
      setAdjustAmount(0)
      setReason("")
      queryClient.invalidateQueries({ queryKey: ["admin", "user", userId] })
    },
    onError: () => {
      toast.error("Failed to adjust credits.")
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: (payload: { user_id: string; is_active: boolean }) =>
      apiFetch("/v1/admin/users/toggle-active", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (_, { is_active }) => {
      toast.success(is_active ? "User enabled" : "User disabled")
      setBanDialogOpen(false)
      queryClient.invalidateQueries({ queryKey: ["admin", "user", userId] })
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] })
    },
    onError: () => {
      toast.error("Failed to update user status.")
    },
  })

  const tierBadgeClass = (tier: string) => {
    if (tier === "pro") return "bg-primary/10 text-primary"
    if (tier === "team") return "bg-accent/30 text-foreground"
    return "bg-secondary text-muted-foreground"
  }

  const txTypeBadge = (type: string) => {
    if (type === "admin_adjustment")
      return "bg-warning/10 text-warning"
    if (type === "usage")
      return "bg-info/10 text-info"
    return "bg-secondary text-muted-foreground"
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-6 max-w-3xl">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-48 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="p-6">
        <p className="text-destructive">User not found.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Back link */}
      <Link
        href="/admin/users"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground
                   hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        All Users
      </Link>

      {/* User info card */}
      <div className="bg-card rounded-2xl border border-border p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="font-serif text-2xl text-foreground">{user.email}</h1>
            <div className="flex items-center gap-3 mt-2">
              <span className={`px-2 py-0.5 rounded-full text-xs font-mono ${tierBadgeClass(user.tier)}`}>
                {user.tier.toUpperCase()}
              </span>
              <span className={`
                px-2 py-0.5 rounded-full text-xs font-mono
                ${user.is_active ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}
              `}>
                {user.is_active ? "ACTIVE" : "DISABLED"}
              </span>
            </div>
          </div>
          {/* Ban/Unban button */}
          <Button
            variant={user.is_active ? "outline" : "default"}
            onClick={() => setBanDialogOpen(true)}
            className={`rounded-full min-h-[44px] px-4 ${
              user.is_active
                ? "border-destructive text-destructive hover:bg-destructive/10"
                : "bg-success text-success-foreground hover:bg-success/90"
            }`}
          >
            {user.is_active ? (
              <><Ban className="w-4 h-4 mr-1.5" /> Disable Account</>
            ) : (
              <><CheckCircle className="w-4 h-4 mr-1.5" /> Enable Account</>
            )}
          </Button>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border">
          <div>
            <p className="text-xs font-mono text-muted-foreground tracking-wider uppercase mb-1">
              Credits
            </p>
            <p className="font-mono text-xl font-bold text-foreground">
              {user.credits_balance.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs font-mono text-muted-foreground tracking-wider uppercase mb-1">
              Sources
            </p>
            <p className="font-mono text-xl font-bold text-foreground">
              {user.sources_count.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs font-mono text-muted-foreground tracking-wider uppercase mb-1">
              Joined
            </p>
            <p className="font-mono text-sm font-bold text-foreground">
              {new Date(user.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Quick action: Adjust credits */}
        <div className="pt-2">
          <Button
            variant="outline"
            onClick={() => setCreditDialogOpen(true)}
            className="rounded-full"
          >
            <Coins className="w-4 h-4 mr-1.5" />
            Adjust Credits
          </Button>
        </div>
      </div>

      {/* Credit Transaction History */}
      <div className="bg-card rounded-2xl border border-border overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-medium text-foreground">Credit History</h2>
          <span className="text-xs font-mono text-muted-foreground ml-auto">
            Last 20 transactions
          </span>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-secondary/50">
              <TableHead className="font-mono text-xs uppercase">Type</TableHead>
              <TableHead className="font-mono text-xs uppercase text-right">Amount</TableHead>
              <TableHead className="font-mono text-xs uppercase text-right">Balance After</TableHead>
              <TableHead className="font-mono text-xs uppercase">Description</TableHead>
              <TableHead className="font-mono text-xs uppercase">Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {user.credit_transactions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-sm text-muted-foreground">
                  No credit transactions yet
                </TableCell>
              </TableRow>
            ) : (
              user.credit_transactions.map((tx) => (
                <TableRow key={tx.id} className="hover:bg-secondary/20">
                  <TableCell>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-mono ${txTypeBadge(tx.type)}`}>
                      {tx.type.toUpperCase()}
                    </span>
                  </TableCell>
                  <TableCell className={`text-right font-mono text-sm ${
                    tx.amount > 0 ? "text-success" : "text-destructive"
                  }`}>
                    {tx.amount > 0 ? "+" : ""}{tx.amount.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm text-foreground">
                    {tx.balance_after.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                    {tx.description}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground font-mono">
                    {new Date(tx.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Ban/Unban Confirmation Dialog */}
      <Dialog open={banDialogOpen} onOpenChange={setBanDialogOpen}>
        <DialogContent className="rounded-2xl max-w-sm">
          <DialogHeader>
            <DialogTitle>
              {user.is_active ? "Disable Account?" : "Enable Account?"}
            </DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground">
              {user.is_active
                ? `This will prevent ${user.email} from logging in. This action can be reversed.`
                : `This will allow ${user.email} to log in again.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setBanDialogOpen(false)}
              className="rounded-full"
            >
              Cancel
            </Button>
            <Button
              onClick={() =>
                toggleActiveMutation.mutate({
                  user_id: user.id,
                  is_active: !user.is_active,
                })
              }
              className={`rounded-full ${
                user.is_active
                  ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  : "bg-success text-success-foreground hover:bg-success/90"
              }`}
            >
              {user.is_active ? "Disable Account" : "Enable Account"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Credit Adjustment Dialog */}
      <Dialog
        open={creditDialogOpen}
        onOpenChange={(o) => {
          if (!o) {
            setCreditDialogOpen(false)
            setAdjustAmount(0)
            setReason("")
          }
        }}
      >
        <DialogContent className="rounded-2xl max-w-sm">
          <DialogHeader>
            <DialogTitle>Adjust Credits — {user.email}</DialogTitle>
          </DialogHeader>

          {/* Current balance */}
          <div className="bg-secondary/50 rounded-xl px-4 py-3 text-center">
            <p className="text-xs font-mono text-muted-foreground mb-1">Current Balance</p>
            <p className="font-mono text-2xl font-bold text-foreground">
              {user.credits_balance.toLocaleString()}
            </p>
          </div>

          {/* Stepper */}
          <div className="flex items-center justify-center gap-4">
            <Button
              variant="outline"
              size="icon"
              className="w-10 h-10 rounded-full"
              onClick={() => setAdjustAmount((a) => a - 100)}
            >
              <Minus className="w-4 h-4" />
            </Button>
            <input
              type="number"
              value={adjustAmount}
              onChange={(e) => setAdjustAmount(parseInt(e.target.value) || 0)}
              className="w-28 text-center font-mono text-2xl font-bold border border-border
                         rounded-xl px-3 py-2 outline-none bg-card
                         focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
            <Button
              variant="outline"
              size="icon"
              className="w-10 h-10 rounded-full"
              onClick={() => setAdjustAmount((a) => a + 100)}
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>

          {adjustAmount !== 0 && (
            <p className="text-center text-xs font-mono text-muted-foreground">
              New balance:{" "}
              <span className={adjustAmount > 0 ? "text-success" : "text-destructive"}>
                {(user.credits_balance + adjustAmount).toLocaleString()}
              </span>
            </p>
          )}

          {/* Reason */}
          <div className="space-y-1.5">
            <label htmlFor="reason" className="text-sm font-medium text-foreground">
              Reason <span className="text-destructive">*</span>
            </label>
            <textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Describe why you are adjusting credits (min 10 characters)..."
              rows={3}
              className="w-full rounded-xl border border-border px-3 py-2.5 text-sm
                         outline-none bg-card resize-none
                         focus:ring-2 focus:ring-primary/30 focus:border-primary
                         placeholder:text-muted-foreground"
            />
            {reason.length > 0 && reason.length < 10 && (
              <p className="text-xs text-destructive">
                {10 - reason.length} more characters required
              </p>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setCreditDialogOpen(false)} className="rounded-full">
              Cancel
            </Button>
            <Button
              onClick={() =>
                adjustMutation.mutate({
                  user_id: user.id,
                  amount: adjustAmount,
                  reason,
                })
              }
              disabled={adjustAmount === 0 || reason.length < 10}
              className="rounded-full bg-primary text-primary-foreground
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {adjustAmount > 0
                ? `Add ${adjustAmount} credits`
                : adjustAmount < 0
                ? `Remove ${Math.abs(adjustAmount)} credits`
                : "Set amount"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

═══════════════════════════════════════════════════════════════════
LOADING STATES — required (RULE 10)
═══════════════════════════════════════════════════════════════════

FILE: app/(admin)/loading.tsx

import { Skeleton } from "@/components/ui/skeleton"

export default function AdminLoading() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-10 w-40 rounded-full" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-2xl" />
        ))}
      </div>
      <Skeleton className="h-40 rounded-2xl" />
    </div>
  )
}

FILE: app/(admin)/users/loading.tsx

import { Skeleton } from "@/components/ui/skeleton"

export default function AdminUsersLoading() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-32 mt-1" />
      </div>
      {/* Search + filter skeleton */}
      <div className="flex gap-3">
        <Skeleton className="h-10 flex-1 rounded-xl" />
        <Skeleton className="h-9 w-32 rounded-full" />
        <Skeleton className="h-9 w-28 rounded-full" />
      </div>
      {/* Table skeleton */}
      <div className="bg-card rounded-2xl border border-border overflow-hidden">
        <div className="p-4 space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-4">
              <Skeleton className="h-5 w-56" />
              <Skeleton className="h-5 w-12" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-20" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

FILE: app/(admin)/users/[id]/loading.tsx

import { Skeleton } from "@/components/ui/skeleton"

export default function AdminUserDetailLoading() {
  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <Skeleton className="h-5 w-24" />
      <Skeleton className="h-48 rounded-2xl" />
      <Skeleton className="h-64 rounded-2xl" />
    </div>
  )
}

═══════════════════════════════════════════════════════════════════
ANTI-PATTERNS
═══════════════════════════════════════════════════════════════════

❌ ◆ ADMIN_PANEL in green → must be text-destructive (RED)
❌ <form> tag anywhere → use onClick + controlled state only
❌ rounded-lg on cards → must be rounded-2xl
❌ rounded-md on CTAs → must be rounded-full
❌ credit adjustment: amount = 0 → disabled button
❌ credit adjustment: reason < 10 chars → disabled button
❌ No loading.tsx for any admin page (stats, users list, user detail)
❌ Non-admin user reaching /admin → must redirect silently to /dashboard
❌ Ban/unban without confirmation dialog
❌ Show full credit card number or password in UI — never expose sensitive data
❌ Use bg-background on sidebar → must be bg-primary
❌ Touch targets below 44px on mobile

═══════════════════════════════════════════════════════════════════
STEP-BY-STEP IMPLEMENTATION PHASES
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss — Phase 2

Phase 2a: Verify API client has admin endpoint types
  grep -rn "admin/users\|admin/stats\|admin/credits" src/lib/api-client/ --include="*.ts"
  If not found → npm run generate-client

Phase 2b: Create admin layout
  File: app/(admin)/layout.tsx
  - Check admin IDs from ADMIN_USER_IDS env var (server-side)
  - Redirect non-admins to /dashboard
  - Header with red ◆ ADMIN_PANEL mono label
  - "use client" directive NOT needed (auth() is server-side)

Phase 2c: Create stats page
  File: app/(admin)/page.tsx
  - 6 stat cards in 3-column grid
  - LLM spend progress bar
  - Sources/metadocs today counters
  - TanStack Query with staleTime: 30_000

Phase 2d: Create user list page
  File: app/(admin)/users/page.tsx
  - Search + tier filter pills + status filter pills
  - Paginated table with all columns
  - DropdownMenu with View details, Adjust credits, Enable/Disable
  - Credit adjustment dialog with stepper + reason textarea
  - TanStack Query with staleTime: 30_000

Phase 2e: Create user detail page
  File: app/(admin)/users/[id]/page.tsx
  - Back link to /admin/users
  - User info card with tier badge, status badge, credit balance
  - Ban/Unban button with confirmation dialog
  - Adjust credits button → same dialog as list page
  - Credit transaction history table
  - TanStack Query with staleTime: 30_000

Phase 2f: Create all loading states
  Files: app/(admin)/loading.tsx, app/(admin)/users/loading.tsx, app/(admin)/users/[id]/loading.tsx
  - Skeleton matching each page's structure

INVOKE: Use /tailwindcss-animations — Phase 3

Phase 3: Verify micro-interactions
  - DropdownMenu opens with scale(0.95)→scale(1) animation (shadcn default)
  - Credit dialog has smooth open/close
  - Progress bar transitions: transition-all duration-500
  - Card hover: hover:shadow-md transition-shadow duration-150

INVOKE: Use /superpowers:verification-before-completion — Phase 4

Phase 4: AC verification and final checks
  Run all grep commands below. Fix any violations.

═══════════════════════════════════════════════════════════════════
AC-BY-AC VERIFICATION TABLE
═══════════════════════════════════════════════════════════════════

For each frontend AC, write a one-line verification result:

□ AC-7: Admin layout — VERIFIED (grep: process.env.ADMIN_USER_IDS in layout.tsx + redirect("/dashboard"))
□ AC-8: Stats page 4+ cards — VERIFIED (statCards array has 6 items, LLM spend progress bar exists)
□ AC-8: LLM spend cap shown — VERIFIED (shows $X / $Y format)
□ AC-9: Search input calls /v1/admin/users?search= — VERIFIED (URLSearchParams in queryFn)
□ AC-9: Tier filter pills — VERIFIED (tierPillClass with bg-primary when active)
□ AC-9: Status filter pills — VERIFIED (statusPillClass)
□ AC-9: Table columns: email, tier badge, credits, status, joined, actions — VERIFIED
□ AC-9: DropdownMenu with View details, Adjust credits, Disable/Enable — VERIFIED
□ AC-10: User detail page at /admin/users/[id] — VERIFIED (file exists)
□ AC-10: Credit transaction history table — VERIFIED (Table component with tx rows)
□ AC-10: Ban/unban toggle button — VERIFIED (Button with Ban/CheckCircle icon)
□ AC-11: Amount ≠ 0 validation — VERIFIED (disabled={adjustAmount === 0})
□ AC-11: Reason min 10 chars validation — VERIFIED (disabled={reason.length < 10})
□ AC-11: toast.success on credit adjustment — VERIFIED (adjustMutation.onSuccess)
□ AC-12: ◆ ADMIN_PANEL text-destructive — VERIFIED (className="text-destructive")
□ loading.tsx for all 3 pages — VERIFIED (3 files exist)
□ No <form> tags in any admin page — VERIFIED (grep: 0 results)
□ All className use CSS variables — VERIFIED (grep: 0 hardcoded hex in admin pages)

Run grep verification commands:
grep -rn "className.*#2d4a3e\|className.*#f5f3ee" app/\(admin\)/
# Expected: 0 matches

grep -rn "<form" app/\(admin\)/
# Expected: 0 matches

grep -rn "ADMIN_PANEL" app/\(admin\)/
# Expected: layout.tsx contains text-destructive

ls app/\(admin\)/loading.tsx app/\(admin\)/users/loading.tsx app/\(admin\)/users/\[id\]/loading.tsx
# Expected: all 3 files exist

═══════════════════════════════════════════════════════════════════
SUCCESS CRITERIA — ALL must be YES to report complete
═══════════════════════════════════════════════════════════════════

✅ Admin layout: server-side auth check, redirect to /dashboard for non-admins
✅ ◆ ADMIN_PANEL in text-destructive (RED)
✅ Stats page: 6 stat cards + LLM spend progress bar + activity counters
✅ User list: search + tier filter + status filter + paginated table
✅ Actions dropdown: View details, Adjust credits, Enable/Disable
✅ Credit adjustment dialog: stepper +/-, reason textarea (min 10 chars)
✅ Submit disabled until valid amount + reason
✅ toast.success on successful credit adjustment with new balance
✅ Ban/unban button with confirmation dialog
✅ User detail page: user info card + transaction history + credit form
✅ loading.tsx for all 3 admin pages
✅ No <form> tags anywhere in admin pages
✅ All className strings use CSS variables (0 hardcoded hex)
✅ npm run build passes (0 TypeScript errors)

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
