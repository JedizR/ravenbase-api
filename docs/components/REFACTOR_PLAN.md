# REFACTOR_PLAN.md — Ravenbase Code Repair & Production Launch

> **Status:** ACTIVE
> **Created:** 2026-04-02
> **Purpose:** Self-contained fix instructions for every known bug + deployment guide

---

## HOW TO USE THIS DOCUMENT

Each section (BUG-xxx, ADMIN-xxx, UX-xxx, DEPLOY-xxx) is SELF-CONTAINED.
An agent can take one section, implement it completely, and move on.
No section depends on another unless marked `DEPENDS ON:`.

Sections are ordered by priority:
- **P0** — must fix before any testing or deployment
- **P1** — must fix before production launch
- **P2** — should fix but not blocking

---

## SECTION INDEX

| ID | Section | Priority | Story | Status |
|---|---|---|---|---|
| BUG-001 | Footer+Header double-render (marketing pages) | P0 | STORY-039 | OPEN |
| BUG-002 | /dashboard returns 404 | P0 | STORY-039 | OPEN |
| BUG-003 | Header backdrop-blur design violation | P0 | STORY-039 | OPEN |
| BUG-004 | Authenticated user visiting / not redirected | P0 | STORY-039 | OPEN |
| BUG-005 | Onboarding completion redirects to /dashboard (404) | P0 | STORY-039 | OPEN |
| BUG-006 | No admin credit bypass — blocks all LLM testing | P0 | STORY-040 | OPEN |
| BUG-009 | Dockerfile.api has --reload (dev-only flag in prod) | P0 | STORY-039 | OPEN |
| BUG-010 | vercel.json missing — no security headers | P0 | STORY-041 | OPEN |
| BUG-011 | ADMIN_USER_IDS is placeholder in both repos | P0 | STORY-040 | OPEN |
| BUG-012 | bg-white hardcoded in PricingToggle | P1 | STORY-039 | OPEN |
| BUG-013 | "How it works" nav link broken on /pricing, /terms | P1 | STORY-039 | OPEN |
| BUG-014 | Fake testimonials with TODO comment | P1 | STORY-041 | OPEN |
| BUG-015 | CRITICAL: Delete Account shows success without calling API | P0 | STORY-039 | OPEN |
| BUG-016 | MetaDocEditor auto-save not implemented (RULE-19 violation) | P0 | STORY-039 | OPEN |
| BUG-017 | MetaDocHistory clicking doc sets activeContent="" | P0 | STORY-039 | OPEN |
| BUG-018 | Graph date range filter UI never applied to nodes | P1 | STORY-039 | OPEN |
| BUG-019 | No ErrorBoundary in dashboard layout | P1 | STORY-039 | OPEN |
| BUG-020 | Missing skip link in dashboard layout (WCAG 2.1 AA) | P1 | STORY-039 | OPEN |
| BUG-021 | Omnibar /search and /generate show "not implemented" toast | P1 | STORY-041 | OPEN |
| BUG-022 | MemoryChat ReadableStream not cancelled on unmount | P1 | STORY-039 | OPEN |
| BUG-023 | Notification preferences test email endpoint 404 | P1 | STORY-039 | OPEN |
| BUG-024 | Data export status uses wrong query param format | P1 | STORY-039 | OPEN |
| BUG-025 | GraphQueryBar example clicks don't auto-execute | P2 | STORY-041 | OPEN |
| BUG-026 | Admin stats page uses inline style for progress bar | P2 | STORY-041 | OPEN |
| BUG-027 | PricingSection "Open dashboard" links to /dashboard (404) | P0 | STORY-039 | OPEN |
| BUG-028 | MemoryInbox activeIndex out of bounds on last resolve | P1 | STORY-039 | OPEN |
| BUG-029 | Profile color selector inline style may not render | P2 | STORY-041 | OPEN |
| BUG-030 | Duplicate color var(--accent) in COLOR_OPTIONS | P2 | STORY-041 | OPEN |
| BUG-031 | Loading skeletons don't match actual page structure | P2 | STORY-041 | OPEN |
| BUG-032 | ProfileContext casts API responses without Zod validation | P1 | STORY-039 | OPEN |
| BUG-033 | Checkout URL not validated before redirect | P1 | STORY-039 | OPEN |
| ADMIN-001 | Backend CreditService admin bypass | P0 | STORY-040 | OPEN |
| ADMIN-002 | GET /v1/me extend with is_admin | P0 | STORY-040 | OPEN |
| ADMIN-003 | Frontend Sidebar admin indicator | P0 | STORY-040 | OPEN |
| ADMIN-004 | Frontend Pricing page admin view | P0 | STORY-040 | OPEN |
| UX-001 | Wire IngestionDropzone into Sources page | P0 | STORY-041 | OPEN |
| UX-002 | Verify dark mode toggle writes .dark to <html> | P1 | STORY-041 | OPEN |
| UX-003 | Verify HeroSection has dual CTA | P1 | STORY-041 | OPEN |
| DEPLOY-001 | Create vercel.json | P0 | STORY-041 | OPEN |
| DEPLOY-002 | Fix next.config.mjs image remotePatterns | P0 | STORY-041 | OPEN |
| DEPLOY-003 | Fix Dockerfile.api (remove --reload) | P0 | STORY-039 | OPEN |

---

## PART 1: CRITICAL BUGS (P0)

---

### BUG-001: Footer + Header double-rendered on marketing pages

**Severity:** High
**Files to change:**
- `ravenbase-web/app/(marketing)/page.tsx`
- `ravenbase-web/app/(marketing)/privacy/page.tsx`
- `ravenbase-web/app/(marketing)/terms/page.tsx`

**Root cause:** `app/(marketing)/layout.tsx` renders `<Header>` and `<Footer>` for all children. Each individual page file ALSO imports and renders them → two nav bars, two footers.

**Fix:** In EACH of the three page files, remove these lines:

```typescript
// DELETE these lines from each page file:
import { Header } from "@/components/marketing/Header"
import { Footer } from "@/components/marketing/Footer"
```

And remove the corresponding JSX:
```tsx
// DELETE from JSX in each page:
<Header />
<Footer />
```

Keep: all other content in the file.

**Verification:**
```bash
npm run dev
# Visit http://localhost:3000 → exactly ONE nav bar, ONE footer
# Visit http://localhost:3000/privacy → same
# Visit http://localhost:3000/terms → same
```

---

### BUG-002: /dashboard returns 404

**Severity:** High
**File to CREATE:** `ravenbase-web/app/(dashboard)/page.tsx`

**Root cause:** Route group `(dashboard)` does NOT create a `/dashboard` URL. Any link, bookmark, or redirect to `/dashboard` returns 404.

**Fix:** Create the file:

```tsx
// app/(dashboard)/page.tsx
import { redirect } from "next/navigation"

export default function DashboardPage() {
  redirect("/chat")
}
```

**Also search for all /dashboard references and fix them:**
```bash
grep -r '"/dashboard"' ravenbase-web/ --include="*.tsx" --include="*.ts" -l
# Common locations: OnboardingWizard.tsx, PricingSection.tsx, any "go to dashboard" links
```

**Verification:**
```bash
# http://localhost:3000/dashboard → 307 redirect to /chat (not 404)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/dashboard
# Expected: 307
```

---

### BUG-003: Marketing Header uses backdrop-blur-sm on scroll (design system violation)

**Severity:** Medium
**File to fix:** `ravenbase-web/components/marketing/Header.tsx`

**Root cause:** Line ~36 in the scrolled state className uses `backdrop-blur-sm`. The design system forbids blur effects — `bg-background` is already opaque cream (#f5f3ee), so transparency/blur is unnecessary and wrong.

**Fix:**
```typescript
// Line ~36 — scrolled state:
// BEFORE:
"bg-background/95 backdrop-blur-sm border-b border-border shadow-sm"
// AFTER:
"bg-background border-b border-border shadow-sm"
```

Also search the same file for any other `backdrop-blur` occurrences (mobile menu section) and remove them.

**Verification:**
```bash
npm run dev
# Scroll on http://localhost:3000 → header is solid cream, no blur effect
grep "backdrop-blur" ravenbase-web/components/marketing/Header.tsx
# Expected: 0 results
```

---

### BUG-004: Authenticated user visiting / not redirected to /chat

**Severity:** High
**File to fix:** `ravenbase-web/middleware.ts`

**Root cause:** `middleware.ts` only handles unauthenticated users visiting protected routes. It has no branch for authenticated users on the landing page.

**Fix — replace full middleware.ts content:**

```typescript
// ravenbase-web/middleware.ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server"
import { NextResponse } from "next/server"

const isPublicRoute = createRouteMatcher([
  "/",
  "/login(.*)",
  "/register(.*)",
  "/onboarding(.*)",
  "/pricing",
  "/privacy",
  "/terms",
  "/api/webhooks/clerk(.*)",
  "/api/webhooks/stripe(.*)",
])

export default clerkMiddleware(async (auth, request) => {
  const { userId } = await auth()

  // Authenticated users visiting landing page → redirect to app
  if (userId && request.nextUrl.pathname === "/") {
    return NextResponse.redirect(new URL("/chat", request.url))
  }

  // Unauthenticated users visiting protected routes → login
  if (!isPublicRoute(request) && !userId) {
    return NextResponse.redirect(new URL("/login", request.url))
  }
})

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
}
```

**Verification:**
```bash
# Sign in → visit http://localhost:3000/ → immediately goes to /chat
# Sign out → visit http://localhost:3000/ → landing page shows (no redirect)
```

---

### BUG-005: OnboardingWizard completion redirects to /dashboard (404)

**Severity:** High
**File to fix:** `ravenbase-web/components/domain/OnboardingWizard.tsx`

**Root cause:** Lines 97 and 134 (approximately) call `router.push("/dashboard")`. The route `/dashboard` does not exist as a URL — it is a Next.js route group, not a real page.

**Fix — search and replace ALL occurrences:**
```bash
# Find all instances:
grep -n "dashboard" ravenbase-web/components/domain/OnboardingWizard.tsx
```

Replace EVERY instance of:
- `router.push("/dashboard")` → `router.push("/chat")`
- `router.replace("/dashboard")` → `router.replace("/chat")`
- `redirect("/dashboard")` → `redirect("/chat")`
- `href="/dashboard"` → `href="/chat"`

**Verification:**
```bash
# Create a new user account → complete onboarding → lands on /chat (not 404)
grep "dashboard" ravenbase-web/components/domain/OnboardingWizard.tsx
# Expected: 0 results
```

---

### BUG-009: Dockerfile.api has --reload flag (dev-only in production)

**Severity:** Medium
**File to fix:** `ravenbase-api/Dockerfile.api`

**Root cause:** Line ~13 has `--reload` which watches files for hot-reload during development. In production this creates unnecessary file watchers and slows startup.

**Fix:**
```dockerfile
# Line ~13:
# BEFORE:
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# AFTER:
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

Note: `--workers 2` is appropriate for Railway's single-dyno deployment. For a dedicated server, use `--workers 4`.

**Verification:**
```bash
docker build -f ravenbase-api/Dockerfile.api -t ravenbase-api-test ravenbase-api/
docker run --rm -e DATABASE_URL=... ravenbase-api-test &
sleep 5
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

---

### BUG-015: CRITICAL — Delete Account button shows success without calling any API

**Severity:** CRITICAL (user data never actually deleted)
**File to fix:** `ravenbase-web/app/(dashboard)/settings/data/page.tsx`

**Root cause:** Lines 120-123 — the `handleDeleteAccount` function calls `toast.success("Account deleted")` and `router.push("/")` without making any API call. The user sees a success message but their data is NOT deleted.

**Fix — find the handleDeleteAccount function and add the API call:**

```typescript
// In app/(dashboard)/settings/data/page.tsx
// Find: handleDeleteAccount (or similar function name)
// The function currently looks like:
const handleDeleteAccount = async () => {
  // (possibly some confirmation check)
  toast.success("Account deleted")
  router.push("/")
}

// REPLACE with:
const handleDeleteAccount = async () => {
  try {
    setIsDeleting(true)
    await apiFetch("/v1/account", { method: "DELETE" })
    toast.success("Account deleted. All your data has been permanently removed.")
    router.push("/")
  } catch (error) {
    setIsDeleting(false)
    toast.error("Failed to delete account. Please try again or contact support.")
  }
}
```

**Notes:**
- The backend `DELETE /v1/account` returns `202` immediately and enqueues the deletion job
- The frontend should NOT wait for deletion to complete — just redirect after 202
- The confirmation dialog (user types "DELETE") should remain — only add the API call inside the confirmed handler

**Verification:**
```bash
# 1. Sign in with a test account
# 2. Navigate to /settings/data
# 3. Click "Delete Account" → type "DELETE" → confirm
# 4. Check network tab: DELETE /v1/account request fired (202 response)
# 5. Verify redirect to /
# psql: SELECT * FROM users WHERE id = 'test_user_id'
# Expected: 0 rows (after ARQ worker completes deletion)
```

---

### BUG-016: MetaDocEditor auto-save not implemented (RULE-19 violation)

**Severity:** High
**File to fix:** `ravenbase-web/components/domain/MetaDocEditor.tsx`

**Root cause:** The editor shows `◆ SAVED_JUST_NOW` / `◆ UNSAVED_CHANGES` status labels but never calls `localStorage.setItem()`. The `use-autosave.ts` hook exists but is not connected.

**Fix — wire the autosave hook in MetaDocEditor.tsx:**

```typescript
// Step 1: Import the hook (it already exists at hooks/use-autosave.ts)
import { useAutosave } from "@/hooks/use-autosave"

// Step 2: In MetaDocEditor component, after content state:
const saveStatus = useAutosave(
  content,
  `ravenbase-draft-${profileId}`,
  30_000  // 30 seconds
)

// Step 3: Update the SaveStatus display to use saveStatus from hook:
// REMOVE any manual status state based on SSE events alone
// REPLACE with saveStatus from the hook

// Step 4: On SSE "done" event, trigger an immediate save:
// In the SSE onmessage handler:
if (parsed.type === "done") {
  // Force an immediate save on completion
  try {
    localStorage.setItem(`ravenbase-draft-${profileId}`, content)
  } catch {
    // localStorage write failed — hook will show UNSAVED_CHANGES
  }
}
```

**The useAutosave hook (hooks/use-autosave.ts) — verify it exists and matches:**
```typescript
"use client"
import { useEffect, useRef, useState } from "react"

type SaveStatus = "saved_just_now" | "saved_2_min_ago" | "unsaved_changes"

export function useAutosave(content: string, key: string, intervalMs = 30_000) {
  const [status, setStatus] = useState<SaveStatus>("saved_just_now")
  const lastSavedRef = useRef<string>("")
  const timerRef = useRef<ReturnType<typeof setInterval>>()

  useEffect(() => {
    timerRef.current = setInterval(() => {
      if (content !== lastSavedRef.current) {
        try {
          localStorage.setItem(key, content)
          lastSavedRef.current = content
          setStatus("saved_just_now")
          setTimeout(() => setStatus("saved_2_min_ago"), 2 * 60 * 1000)
        } catch {
          setStatus("unsaved_changes")  // localStorage write failed
        }
      }
    }, intervalMs)
    return () => clearInterval(timerRef.current)
  }, [content, key, intervalMs])

  return status
}
```

**Verification:**
```bash
# 1. Navigate to /workstation
# 2. Generate a Meta-Doc
# 3. After done event: check localStorage in DevTools
#    Application → Local Storage → ravenbase-draft-{profileId} → content present
# 4. Verify "◆ SAVED_JUST_NOW" appears after generation completes
# 5. Wait 30 seconds while editing → verify save triggered again
```

---

### BUG-017: MetaDocHistory clicking a previous doc sets activeContent="" (content never loaded)

**Severity:** High
**File to fix:** `ravenbase-web/components/domain/MetaDocEditor.tsx`

**Root cause:** The `useEffect([docId])` that fetches `GET /v1/metadoc/{docId}` sets `content=""` before the fetch AND the fetch result never updates state correctly (likely a stale closure issue).

**Fix — replace the broken useEffect:**

```typescript
// In MetaDocEditor.tsx — FIND the useEffect that loads existing docs
// It currently looks something like:
useEffect(() => {
  if (!docId) return
  setContent("")  // clears while loading
  apiFetch(`/v1/metadoc/${docId}`)
    .then((d: any) => setContent(d.content || d.content_markdown || ""))
    // ↑ WRONG: may use wrong field name
}, [docId])

// REPLACE with:
useEffect(() => {
  if (!docId) { setContent(""); return }
  apiFetch<{ content_markdown: string }>(`/v1/metadoc/${docId}`)
    .then((d) => setContent(d.content_markdown))  // MUST use content_markdown
    .catch(() => toast.error("Failed to load document"))
}, [docId, apiFetch])
// ↑ apiFetch in deps array prevents stale closure bug
```

**Key fix details:**
- The field name MUST be `content_markdown` (matches backend `MetaDocument` model)
- `apiFetch` must be in the deps array to prevent stale closure
- Do NOT set `content=""` before the fetch — it causes a flash of empty content

**Verification:**
```bash
# 1. Navigate to /workstation
# 2. Generate a Meta-Doc (creates history)
# 3. Click a document in the history sidebar
# 4. Verify: the document content loads (not empty)
# 5. Verify: no "Failed to load document" toast appears
```

---

### BUG-018: Graph Explorer date range filter never applied to filtered nodes

**Severity:** High
**File to fix:** `ravenbase-web/app/(dashboard)/graph/GraphPageClient.tsx`

**Root cause:** Lines 38-70 — `filteredNodes` useMemo collects `dateRange.from` and `dateRange.to` in state but never uses them in the filter calculation.

**Fix — update the filteredNodes useMemo:**

```typescript
// In app/(dashboard)/graph/GraphPageClient.tsx
// Find the filteredNodes useMemo (around line 51) and add date filtering:

const filteredNodes = useMemo(() => {
  return nodes
    .filter(n => nodeTypeFilter.includes(n.type))
    .filter(n => {
      // BUG-018 FIX: date range was collected but never applied
      if (!dateRange.from && !dateRange.to) return true
      const nodeDate = new Date(n.properties?.created_at ?? 0)
      if (dateRange.from && nodeDate < dateRange.from) return false
      if (dateRange.to && nodeDate > dateRange.to) return false
      return true
    })
}, [nodes, nodeTypeFilter, dateRange])
// ↑ dateRange must be in the deps array
```

**Verification:**
```bash
# 1. Navigate to /graph with some nodes
# 2. Open filter panel → set a date range that excludes most nodes
# 3. Verify: graph updates to show only nodes within the date range
# 4. Clear date range → verify: all nodes visible again
```

---

### BUG-019: No ErrorBoundary in dashboard layout

**Severity:** High
**File to fix:** `ravenbase-web/app/(dashboard)/layout.tsx`

**Root cause:** A single component crash in any dashboard page takes down the entire dashboard with a white screen and no user-visible error message.

**Fix — add ErrorBoundary to dashboard layout:**

```tsx
// Step 1: Create a client component for the ErrorBoundary
// app/(dashboard)/DashboardErrorBoundary.tsx
"use client"
import { Component, ReactNode } from "react"

interface Props { children: ReactNode }
interface State { hasError: boolean; error?: Error }

export class DashboardErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-8 gap-4">
          <p className="font-mono text-xs text-muted-foreground">◆ COMPONENT_ERROR</p>
          <p className="font-serif text-xl">Something went wrong</p>
          <p className="text-sm text-muted-foreground max-w-md text-center">
            {this.state.error?.message ?? "An unexpected error occurred"}
          </p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-full text-sm"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

// Step 2: In app/(dashboard)/layout.tsx, wrap children:
import { DashboardErrorBoundary } from "./DashboardErrorBoundary"

// In the layout JSX, wrap the main content area:
<DashboardErrorBoundary>
  {children}
</DashboardErrorBoundary>
```

---

### BUG-020: Missing skip link in dashboard layout (WCAG 2.1 AA violation)

**Severity:** High (accessibility)
**File to fix:** `ravenbase-web/app/(dashboard)/layout.tsx`

**Root cause:** No skip navigation link exists. Screen reader and keyboard users must tab through the entire sidebar navigation on every page load. WCAG 2.1 criterion 2.4.1 requires a bypass mechanism.

**Fix — add skip link as first element in layout:**

```tsx
// In app/(dashboard)/layout.tsx — add as FIRST element inside the layout wrapper:
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4
             focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground
             focus:rounded-md focus:font-medium focus:text-sm"
>
  Skip to main content
</a>

// Also ensure the main content area has the matching id:
<main id="main-content" className="...">
  {children}
</main>
```

---

### BUG-022: MemoryChat ReadableStream not cancelled on unmount (memory leak)

**Severity:** Medium
**File to fix:** `ravenbase-web/components/domain/MemoryChat.tsx`

**Root cause:** Line ~161 — `fetch()` POST SSE stream starts a `ReadableStream.getReader()`. When the component unmounts (user navigates away), the reader is not cancelled → the stream continues consuming memory and network resources.

**Fix — add cleanup via useRef:**

```typescript
// In MemoryChat.tsx

// Add a ref to track the current reader:
const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null)

// When setting up the reader:
const reader = response.body!.getReader()
readerRef.current = reader  // ← store reference

// In the useEffect cleanup (or add one if missing):
useEffect(() => {
  return () => {
    // Cancel the stream reader on unmount
    readerRef.current?.cancel().catch(() => {})
    readerRef.current = null
  }
}, [])
```

---

### BUG-023: Notification preferences test email endpoint will 404

**Severity:** Medium
**File to fix:** `ravenbase-web/app/(dashboard)/settings/notifications/page.tsx`

**Root cause:** Line ~201 — the "Send test email" handler calls `POST /v1/notification-prefs/test` but the update handler at the same line uses `POST /v1/notification-preferences`. The endpoint paths don't match.

**Fix:**
```typescript
// Line ~201 — find the test email handler:
// BEFORE (wrong URL):
await apiFetch("/v1/notification-prefs/test", { method: "POST" })

// AFTER (verify against backend route, likely):
await apiFetch("/v1/notification-preferences/test", { method: "POST" })
```

**Verification:** Check `ravenbase-api/src/api/routes/` for the actual notification endpoint paths.

---

### BUG-024: Data export status uses query param vs expected path param

**Severity:** Medium
**File to fix:** `ravenbase-web/app/(dashboard)/settings/data/page.tsx`

**Root cause:** Line ~102 — polls `GET /v1/account/export?job_id=xxx` (query param) but the backend job status endpoint is likely `GET /v1/jobs/{job_id}` (path param) per `docs/architecture/03-api-contract.md`.

**Fix:**
```typescript
// Line ~102 — find the job polling query:
// BEFORE:
queryFn: () => apiFetch(`/v1/account/export?job_id=${exportJobId}`)

// AFTER (check backend route pattern — likely):
queryFn: () => apiFetch(`/v1/jobs/${exportJobId}`)
```

**Verification:** Check `ravenbase-api/src/api/routes/` for the job status endpoint pattern.

---

### BUG-027: PricingSection "Open dashboard" links to /dashboard (404)

**Severity:** High
**File to fix:** `ravenbase-web/components/marketing/PricingSection.tsx`

**Root cause:** Line ~278 — the "Open dashboard" button for logged-in users links to `/dashboard` which returns 404 (no page exists there).

**Fix:**
```typescript
// Line ~278:
// BEFORE:
href="/dashboard"
// AFTER:
href="/chat"
```

**Verification:**
```bash
grep -n "dashboard" ravenbase-web/components/marketing/PricingSection.tsx
# All /dashboard → /chat
```

---

### BUG-028: MemoryInbox activeIndex out of bounds after last resolve

**Severity:** Medium
**File to fix:** `ravenbase-web/components/domain/MemoryInbox.tsx`

**Root cause:** Lines 149-151 — after resolving the last conflict, `activeIndex` remains at 0 or 1 but the `conflicts` array is now empty. Accessing `conflicts[activeIndex]` returns `undefined` → render crash.

**Fix — clamp activeIndex after each resolution:**

```typescript
// In MemoryInbox.tsx — find the resolution handler (handleResolve or similar)
// After removing the resolved conflict from the array:

const newConflicts = conflicts.filter(c => c.id !== resolvedId)
setConflicts(newConflicts)

// ADD: clamp activeIndex to valid range
setActiveIndex(prev => Math.min(prev, Math.max(0, newConflicts.length - 1)))
```

**Verification:**
```bash
# 1. Navigate to /inbox with exactly 1 conflict
# 2. Resolve it (Enter or Backspace)
# 3. Verify: empty state renders (◆ ALL_CLEAR) — no crash
# 4. Verify: no "Cannot read properties of undefined" error in console
```

---

### BUG-032: ProfileContext casts API responses as unknown without Zod validation

**Severity:** Medium
**File to fix:** `ravenbase-web/contexts/ProfileContext.tsx`

**Root cause:** Lines 75-81 — API response cast as `unknown as Profile[]` without runtime validation. If the backend API shape changes, the app silently breaks with type errors at runtime.

**Fix — add basic Zod validation:**

```typescript
// In contexts/ProfileContext.tsx
// Option A: Add a simple Zod schema:
import { z } from "zod"  // already in the project via shadcn

const ProfileSchema = z.object({
  id: z.string(),
  name: z.string(),
  is_default: z.boolean(),
  icon: z.string().optional(),
  color: z.string().optional(),
})

const ProfilesResponseSchema = z.object({
  profiles: z.array(ProfileSchema),
})

// In the query function:
queryFn: async () => {
  const raw = await apiFetch("/v1/profiles")
  return ProfilesResponseSchema.parse(raw)
},
```

---

### BUG-033: Checkout URL not validated before redirect

**Severity:** Medium
**File to fix:** `ravenbase-web/components/marketing/PricingSection.tsx`

**Root cause:** Lines 145-150 — after `POST /v1/billing/create-checkout-session`, the response `checkout_url` is immediately used in `window.location.href` without validation. A malformed or unexpected URL could redirect users to an unexpected destination.

**Fix — validate URL before redirect:**

```typescript
// Lines 145-150:
const { checkout_url } = await apiFetch<{ checkout_url: string }>(
  "/v1/billing/create-checkout-session",
  { method: "POST", body: JSON.stringify({ tier, annual }) }
)

// ADD validation before redirect:
if (!checkout_url.startsWith("https://checkout.stripe.com/")) {
  toast.error("Invalid checkout URL. Please try again.")
  return
}
window.location.href = checkout_url
```

---

## PART 2: ADMIN BYPASS (P0)

---

### ADMIN-001: Backend CreditService admin bypass

**DEPENDS ON:** BUG-011 (ADMIN_USER_IDS must be set in .env)
**File to fix:** `ravenbase-api/src/services/credit_service.py`

**Root cause:** `CreditService.check_or_raise()` and `CreditService.deduct()` have no admin bypass. Admin users consume credits and eventually get blocked by 402 errors, preventing all LLM feature testing.

**Fix — add admin bypass to both methods:**

```python
# src/services/credit_service.py

# At the top of check_or_raise:
async def check_or_raise(self, db: AsyncSession, user_id: str, amount: int) -> None:
    # Admin bypass — must be first check
    admin_ids = {u.strip() for u in settings.ADMIN_USER_IDS.split(",") if u.strip()}
    if user_id in admin_ids:
        log.info("credit.admin_bypass.check", user_id=user_id, amount=amount)
        return  # Admin users are never blocked by credit checks
    # ... rest of existing implementation unchanged ...

# At the top of deduct:
async def deduct(
    self,
    db: AsyncSession,
    user_id: str,
    amount: int,
    operation: str,
    reference_id: str | None = None,
) -> CreditTransaction:
    # Admin bypass — must be first check
    admin_ids = {u.strip() for u in settings.ADMIN_USER_IDS.split(",") if u.strip()}
    if user_id in admin_ids:
        log.info("credit.admin_bypass.deduct", user_id=user_id, operation=operation)
        return CreditTransaction(
            user_id=uuid.UUID(user_id),
            amount=0,
            balance_after=-1,  # -1 sentinel: indicates admin bypass, not real balance
            operation=f"admin_bypass:{operation}",
            reference_id=reference_id,
        )
    # ... rest of existing implementation unchanged ...
```

**Required imports (add if not present):**
```python
import uuid
```

**Required: `ADMIN_USER_IDS` in settings:**
```python
# In src/core/config.py — verify this field exists:
ADMIN_USER_IDS: str = Field(default="", description="Comma-separated Clerk user IDs with admin access")
```

**Verification:**
```bash
# Set in .envs/.env.dev:
ADMIN_USER_IDS=your_clerk_user_id_here

# Run the server, then:
# 1. Log in as admin user
# 2. Generate a Meta-Doc
# 3. Check: psql -c "SELECT operation, amount FROM credit_transactions WHERE user_id = 'your_id' ORDER BY created_at DESC LIMIT 3;"
# Expected: operation = "admin_bypass:meta_doc_haiku", amount = 0

make quality
```

---

### ADMIN-002: GET /v1/me extend with is_admin

**DEPENDS ON:** ADMIN-001 (settings.ADMIN_USER_IDS must exist)
**Files to find and fix:** Locate the user profile endpoint in `ravenbase-api/src/api/routes/`

```bash
# Find it:
grep -r "def get_me\|/v1/me\|/v1/account/me\|/account/me" ravenbase-api/src/api/routes/ -l
```

**Fix — add is_admin to the response:**

```python
# In the response schema (find the Me/UserProfile schema in src/schemas/):
class MeResponse(BaseModel):
    id: str
    email: str
    tier: str
    credits_balance: int
    is_admin: bool = False  # ADD THIS FIELD

# In the route handler:
@router.get("/me", response_model=MeResponse)
async def get_me(user: dict = Depends(require_user), db: AsyncSession = Depends(get_db)):
    # ... existing user lookup ...
    admin_ids = {u.strip() for u in settings.ADMIN_USER_IDS.split(",") if u.strip()}
    is_admin = user["user_id"] in admin_ids  # ADD THIS LINE
    return MeResponse(
        **existing_fields,
        is_admin=is_admin  # ADD THIS TO RESPONSE
    )
```

**Verification:**
```bash
# With admin JWT:
curl http://localhost:8000/v1/me \
  -H "Authorization: Bearer ADMIN_JWT"
# Expected: {..., "is_admin": true}

# With regular user JWT:
curl http://localhost:8000/v1/me \
  -H "Authorization: Bearer REGULAR_JWT"
# Expected: {..., "is_admin": false}
```

---

### ADMIN-003: Frontend Sidebar admin indicator

**DEPENDS ON:** ADMIN-002 (GET /v1/me must return is_admin)
**File to fix:** `ravenbase-web/components/domain/Sidebar.tsx`

**Root cause:** Sidebar always shows credit balance. Admin users should see `◆ ADMIN_ACCESS` instead.

**Fix — add admin check in sidebar credits display:**

```typescript
// In Sidebar.tsx — find where credits balance is displayed (near bottom of sidebar)

// Add a query for current user data (may already exist):
const { data: userData } = useQuery({
  queryKey: ["me"],
  queryFn: () => apiFetch<{ is_admin: boolean; credits_balance: number }>("/v1/me"),
  staleTime: 60_000,
})

// Replace the credits display with conditional:
{userData?.is_admin ? (
  <p className="font-mono text-xs text-muted-foreground">◆ ADMIN_ACCESS</p>
) : (
  <div className="flex items-center gap-1">
    <p className="font-mono text-xs text-muted-foreground">
      {userData?.credits_balance ?? "—"} credits
    </p>
  </div>
)}
```

**Design system compliance:**
- `◆ ADMIN_ACCESS` text: `font-mono text-xs text-muted-foreground`
- This is displayed in the sidebar which has `bg-primary` (green) background
- `text-muted-foreground` on `bg-primary` — verify contrast, may need `text-primary-foreground/70`

**Verification:**
```bash
# 1. Log in as admin user
# 2. Verify: sidebar shows "◆ ADMIN_ACCESS" (not a credit count)
# 3. Log in as regular user
# 4. Verify: sidebar shows credit balance (e.g., "500 credits")
```

---

### ADMIN-004: Frontend Pricing page admin view

**DEPENDS ON:** ADMIN-002 (GET /v1/me must return is_admin)
**File to fix:** `ravenbase-web/app/(marketing)/pricing/page.tsx` (or the PricingSection component)

**Root cause:** Pricing page shows upgrade CTAs and tier cards to all users including admins. Admin users have full access and should see a message instead.

**Fix — add admin bypass display:**

```typescript
// In pricing page or PricingSection component:

// Fetch user data (only when authenticated):
const { data: userData } = useQuery({
  queryKey: ["me"],
  queryFn: () => apiFetch<{ is_admin: boolean; tier: string }>("/v1/me"),
  staleTime: 60_000,
  enabled: !!isSignedIn,  // only fetch when user is logged in
})

// In JSX — wrap tier cards with admin check:
{userData?.is_admin ? (
  <div className="text-center py-16 space-y-4">
    <p className="font-mono text-xs text-muted-foreground tracking-wider">◆ ADMIN_ACCOUNT</p>
    <p className="font-serif text-3xl text-foreground">Full access bypass active</p>
    <p className="text-muted-foreground max-w-md mx-auto">
      All features unlocked. Credits and billing are disabled for admin accounts.
    </p>
  </div>
) : (
  {/* existing tier cards */}
)}
```

**Verification:**
```bash
# 1. Log in as admin user
# 2. Navigate to /pricing
# 3. Verify: "◆ ADMIN_ACCOUNT" + "Full access bypass active" shown instead of tier cards
# 4. Log in as regular user
# 5. Verify: normal tier cards shown
```

---

## PART 3: DEPLOYMENT CONFIG (P0)

---

### DEPLOY-001: Create vercel.json

**File to CREATE:** `ravenbase-web/vercel.json`

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Strict-Transport-Security", "value": "max-age=31536000; includeSubDomains" },
        { "key": "Permissions-Policy", "value": "geolocation=(), microphone=(), camera=()" }
      ]
    },
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "no-store" }
      ]
    }
  ],
  "redirects": [
    {
      "source": "/dashboard",
      "destination": "/chat",
      "permanent": false
    }
  ]
}
```

**Verification:**
```bash
npx vercel dev
# Check response headers: curl -I http://localhost:3000/
# Expected: X-Frame-Options: DENY, X-Content-Type-Options: nosniff, etc.
```

---

### DEPLOY-002: Fix next.config.mjs image remotePatterns

**File to fix:** `ravenbase-web/next.config.mjs`

**Root cause:** Production images from Clerk, Supabase, and Unsplash will fail to load if their hostnames aren't in `remotePatterns`.

**Fix — replace next.config.mjs:**

```javascript
// ravenbase-web/next.config.mjs
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "img.clerk.com",
      },
      {
        protocol: "https",
        hostname: "*.supabase.co",
      },
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
}

export default nextConfig
```

---

### DEPLOY-003: Fix Dockerfile.api

See BUG-009 above. This is the same fix (remove `--reload`, add `--workers 2`).

---

## PART 4: UX GAPS (P1)

---

### UX-001: Wire IngestionDropzone into Sources page

**File to fix:** `ravenbase-web/app/(dashboard)/sources/page.tsx`

**Root cause:** The Upload Files tab currently shows placeholder "coming soon" text. `IngestionDropzone` component exists at `components/domain/IngestionDropzone.tsx` but is not wired in.

**Fix — replace placeholder with actual component:**

```typescript
// In app/(dashboard)/sources/page.tsx
// Find the Upload tab content — it looks like:
// <p>File upload coming soon</p>
// or
// <div>Coming soon</div>

// REPLACE with:
import { IngestionDropzone } from "@/components/domain/IngestionDropzone"

// In the Upload tab panel:
<IngestionDropzone
  profileId={activeProfileId}
  onUploadComplete={(jobId) => {
    // Optionally track progress
    toast.success("File upload started")
    queryClient.invalidateQueries({ queryKey: ["sources"] })
  }}
/>
```

**Notes:**
- `IngestionDropzone` accepts `profileId: string` and calls `POST /v1/ingest/upload`
- After upload, invalidate the `sources` TanStack Query key to refresh the sources list
- `IngestionProgress` component (if it exists) can be added below the dropzone to show SSE progress

**Verification:**
```bash
# 1. Navigate to /sources
# 2. Click "Upload Files" tab
# 3. Verify: dropzone renders (not "coming soon")
# 4. Drop a PDF → verify upload fires → source appears in list after processing
```

---

### UX-002: Verify dark mode toggle writes .dark to <html>

**File to check/fix:** `ravenbase-web/hooks/use-theme.ts` (or similar)

**Required behavior:**
- Dark mode toggle must write `.dark` to `document.documentElement` (the `<html>` element)
- NOT to `document.body` or any inner element
- Must persist to `localStorage` with key `theme`
- Must apply class before first paint to prevent flash (check `layout.tsx` for hydration)

**Verification:**
```typescript
// In DevTools → Elements → <html> element:
// Light mode: class="" (or class="[fonts]")
// Dark mode: class="dark [fonts]"
// NOT: class="dark" on <body> or any inner div

// Also verify in hooks/use-theme.ts:
document.documentElement.classList.toggle("dark", isDark)  // ← correct
// NOT:
document.body.classList.toggle("dark", isDark)  // ← wrong
```

---

### UX-003: Verify HeroSection has dual CTA

**File to check/fix:** `ravenbase-web/components/marketing/HeroSection.tsx`

**Required:** Two CTAs in the hero:
1. Primary: "Start for free →" (rounded-full, bg-primary)
2. Secondary: "Watch demo" or "How it works" (rounded-full, variant="outline")

**Fix if only one CTA exists:**
```tsx
// In HeroSection.tsx — add secondary CTA:
<div className="flex flex-col sm:flex-row gap-4 justify-center">
  <Button variant="default" className="rounded-full" asChild>
    <Link href="/register">Start for free →</Link>
  </Button>
  <Button variant="outline" className="rounded-full" asChild>
    <Link href="#how-it-works">How it works</Link>
  </Button>
</div>
```

---

## PART 5: REMAINING P1/P2 BUGS (Quick Fixes)

---

### BUG-012: bg-white hardcoded in PricingToggle

**File:** `ravenbase-web/components/marketing/PricingToggle.tsx`
**Fix:**
```typescript
// Line ~33:
// BEFORE: className="bg-white ..."
// AFTER:  className="bg-secondary ..."
```

---

### BUG-013: "How it works" nav link broken on /pricing and /terms

**File:** `ravenbase-web/components/marketing/Header.tsx`
**Root cause:** NAV_LINKS includes `{ href: "/#how-it-works", label: "How it works" }`. This anchor only exists on the landing page `/` — not on `/pricing` or `/terms`.
**Fix:** Either (a) conditionally hide this nav link on non-landing pages, or (b) always use `/#how-it-works` (with the hash, it navigates to `/` then scrolls).
```typescript
// Option B (simpler): ensure href is "/#how-it-works" not "#how-it-works"
// This navigates to the landing page and scrolls to that section
{ href: "/#how-it-works", label: "How it works" }
```

---

### BUG-014: Fake testimonials with TODO comment

**File:** `ravenbase-web/components/marketing/TestimonialsSection.tsx`
**Action:** Either (a) replace with real testimonials, or (b) remove the testimonials section entirely until real ones are available. Do NOT launch with fake testimonials.
**Recommended fix:** Remove `TestimonialsSection` from the landing page until real testimonials are available. Update `app/(marketing)/page.tsx` to not render it.

---

### BUG-025: GraphQueryBar example clicks don't auto-execute

**File:** `ravenbase-web/components/domain/GraphQueryBar.tsx`
**Fix:**
```typescript
// Line ~91 — onClick for example queries:
// BEFORE: onClick={() => setInput(exampleQuery)}
// AFTER:
onClick={() => {
  setInput(exampleQuery)
  handleSubmit(exampleQuery)  // auto-execute after filling
}}
```

---

### BUG-026: Admin stats page uses inline style for progress bar

**File:** `ravenbase-web/app/admin/page.tsx`
**Fix:**
```tsx
// Lines 107-109 — instead of style={{ width: `${percentage}%` }}
// Use Tailwind's arbitrary value:
// BEFORE: style={{ width: `${percentage}%` }}
// AFTER: className={`bg-primary h-2 rounded-full`} style={{ width: `${percentage}%` }}
// Note: inline width for progress bars is acceptable since % is dynamic
// The violation is using style for colors/spacing that should be tokens
// Verify the colors use proper token classes, not hardcoded hex values
```

---

### BUG-029: Profile color selector inline style may not render

**File:** `ravenbase-web/app/(dashboard)/settings/profiles/page.tsx`
**Root cause:** Line ~154 uses `style={{ backgroundColor: c.value }}` where `c.value` is a CSS variable string like `var(--primary)`. Inline styles don't process CSS variables the same way as Tailwind classes.
**Fix:**
```tsx
// BEFORE: style={{ backgroundColor: c.value }}
// AFTER: Use the appropriate bg- class:
// Map color values to Tailwind classes:
const colorClassMap: Record<string, string> = {
  "var(--primary)": "bg-primary",
  "var(--accent)": "bg-accent",
  "var(--warning)": "bg-warning",
  // etc.
}
// Then: className={colorClassMap[c.value] ?? "bg-secondary"}
```

---

### BUG-030: Duplicate color var(--accent) in COLOR_OPTIONS

**File:** `ravenbase-web/app/(dashboard)/settings/profiles/page.tsx`
**Fix:**
```typescript
// Line ~24 and ~27: two entries with value: "var(--accent)"
// Remove the duplicate. Keep only one.
const COLOR_OPTIONS = [
  { label: "Forest", value: "var(--primary)" },
  { label: "Sage", value: "var(--accent)" },  // keep this one
  { label: "Amber", value: "var(--warning)" },
  // remove the duplicate var(--accent)
]
```

---

## PART 6: DEPLOYMENT — RAILWAY (Backend)

**Prerequisites (user must complete before this phase):**

1. Create Railway account at railway.app
2. Create Qdrant Cloud account at cloud.qdrant.io (free tier)
3. Create Neo4j AuraDB at neo4j.com/cloud/aura (free tier)
4. Create Supabase project at supabase.com (free tier)
5. Create Stripe account at stripe.com
6. Create Resend account at resend.com
7. Create Anthropic API key at console.anthropic.com
8. Create OpenAI API key at platform.openai.com
9. Create Google AI key at aistudio.google.com
10. Get Clerk PRODUCTION application keys (separate from dev)

**Step 1: Connect GitHub repo**

Railway Dashboard → New Project → Deploy from GitHub → select `ravenbase-api`

**Step 2: Create two services**

```
Service 1: "api"
  Source: GitHub → ravenbase-api repo
  Dockerfile: Dockerfile.api
  Port: 8000

Service 2: "worker"
  Source: same GitHub repo
  Dockerfile: Dockerfile.worker
  No port
```

**Step 3: Add PostgreSQL and Redis**

Railway → Project → New → Database → PostgreSQL → name it "ravenbase-db"
Railway → Project → New → Database → Redis → name it "ravenbase-redis"

Both auto-inject `DATABASE_URL` and `REDIS_URL` into your services.

**Step 4: Environment variables (set for BOTH api and worker services)**

```
DATABASE_URL             = [auto-injected by Railway PostgreSQL]
REDIS_URL                = [auto-injected by Railway Redis]
QDRANT_URL               = https://[xxx].qdrant.io
QDRANT_API_KEY           = [from Qdrant Cloud dashboard → API Keys]
NEO4J_URI                = neo4j+s://[xxx].databases.neo4j.io
NEO4J_USER               = neo4j
NEO4J_PASSWORD           = [from AuraDB instance creation page]
OPENAI_API_KEY           = sk-[from platform.openai.com → API Keys]
ANTHROPIC_API_KEY        = sk-ant-[from console.anthropic.com]
GEMINI_API_KEY           = AIzaSy[from aistudio.google.com → API Key]
SUPABASE_URL             = https://[project-id].supabase.co
SUPABASE_SERVICE_ROLE_KEY = eyJhb...[from Supabase → Settings → API → service_role]
STORAGE_BUCKET           = ravenbase-sources
ADMIN_USER_IDS           = [your Clerk PRODUCTION user ID — from Clerk dashboard]
APP_ENV                  = production
ENABLE_PII_MASKING       = true
```

**Step 5: API-only environment variables**

```
CLERK_FRONTEND_API       = [your-app-name].clerk.accounts.dev
CLERK_WEBHOOK_SECRET     = whsec_[from Clerk Production → Webhooks → signing secret]
STRIPE_SECRET_KEY        = sk_live_[from Stripe dashboard]
STRIPE_WEBHOOK_SECRET    = whsec_[from Stripe webhooks page]
STRIPE_PRO_MONTHLY_PRICE_ID  = price_[create in Stripe: Pro Monthly $15/mo]
STRIPE_PRO_ANNUAL_PRICE_ID   = price_[create in Stripe: Pro Annual $144/yr]
STRIPE_TEAM_MONTHLY_PRICE_ID = price_[create in Stripe: Team Monthly $49/mo]
STRIPE_TEAM_ANNUAL_PRICE_ID  = price_[create in Stripe: Team Annual $468/yr]
APP_BASE_URL             = https://ravenbase.app
RESEND_API_KEY           = re_[from Resend dashboard]
RESEND_WEBHOOK_SECRET    = whsec_[from Resend webhooks]
```

**Step 6: Pre-deploy command (API service only)**

Railway → api service → Settings → Deploy → Pre-Deploy Command:
```
uv run alembic upgrade head
```

This runs database migrations before each deploy automatically.

**Step 7: Set custom domain**

Railway → api service → Settings → Domains → Custom Domain: `api.ravenbase.app`
Add CNAME in DNS registrar:
```
api.ravenbase.app → [railway-generated-domain].railway.app
```

**Step 8: Configure Stripe webhook**

Stripe Dashboard → Developers → Webhooks → Add endpoint:
```
URL: https://api.ravenbase.app/webhooks/stripe
Events to listen for:
  - checkout.session.completed
  - customer.subscription.deleted
  - invoice.payment_failed
  - customer.subscription.updated
```
Copy signing secret → set as `STRIPE_WEBHOOK_SECRET` in Railway.

**Step 9: Configure Clerk webhook**

Clerk Production Dashboard → Webhooks → Add endpoint:
```
URL: https://api.ravenbase.app/webhooks/clerk
Events:
  - user.created
  - user.updated
  - user.deleted
```
Copy signing secret → set as `CLERK_WEBHOOK_SECRET` in Railway.

**Step 10: Deploy**

Push to main branch → Railway auto-deploys.

**Step 11: Verify health**

```bash
curl https://api.ravenbase.app/health
# Expected: {"status": "healthy", "postgres": "ok", "redis": "ok"}

curl -s -o /dev/null -w "%{http_code}" https://api.ravenbase.app/v1/conflicts
# Expected: 401 (auth required — not 404, not 500)

curl -s -o /dev/null -w "%{http_code}" -X POST https://api.ravenbase.app/webhooks/clerk
# Expected: 400 (missing signature — not 404)
```

---

## PART 7: DEPLOYMENT — VERCEL (Frontend)

**Prerequisites:**
- Vercel account created
- `ravenbase-web` GitHub repo connected to Vercel
- Clerk PRODUCTION application created (pk_live_... keys)
- `ravenbase-api` already deployed at api.ravenbase.app (Part 6 complete)
- Custom domain ravenbase.app configured in Vercel

**Step 1: Environment variables in Vercel Dashboard**

Project → Settings → Environment Variables → Add for Production:

```
NEXT_PUBLIC_API_URL              = https://api.ravenbase.app
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = pk_live_[from Clerk Production → API Keys]
CLERK_SECRET_KEY                  = sk_live_[from Clerk Production → API Keys]
NEXT_PUBLIC_CLERK_SIGN_IN_URL    = /login
NEXT_PUBLIC_CLERK_SIGN_UP_URL    = /register
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL = /chat
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL = /onboarding
CLERK_WEBHOOK_SECRET             = whsec_[same as set in Railway]
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = pk_live_[from Stripe dashboard]
ADMIN_USER_IDS                   = [your Clerk PRODUCTION user ID]
```

**Step 2: Configure Clerk Production Application**

Clerk Dashboard → Production App → Settings:
```
Home URL:              https://ravenbase.app
Sign-in URL:           https://ravenbase.app/login
Sign-up URL:           https://ravenbase.app/register
After sign-in URL:     https://ravenbase.app/chat
After sign-up URL:     https://ravenbase.app/onboarding
```

Add allowed origins: `https://ravenbase.app`

**Step 3: Local build verification**

```bash
cd ravenbase-web
npm run build
# Must output: ✓ Compiled successfully (0 TypeScript errors, 0 warnings)
# If errors: fix them before deploying
```

**Step 4: Deploy**

```bash
git push origin main
# Vercel auto-deploys from main branch

# OR manually:
npx vercel --prod
```

**Step 5: Set custom domain**

Vercel → Project → Settings → Domains → Add Domain: `ravenbase.app`
Add records in DNS registrar per Vercel's instructions.

**Step 6: Post-deploy verification**

```bash
curl -I https://ravenbase.app
# Expected: HTTP/2 200

curl -I https://ravenbase.app/chat
# Expected: HTTP/2 307 (redirect to /login if not authenticated)

curl -I https://ravenbase.app/dashboard
# Expected: HTTP/2 307 (redirect to /chat per vercel.json)

curl -s https://ravenbase.app/ | grep "Ravenbase"
# Expected: page title contains "Ravenbase"
```

---

## PART 8: NEW STORIES

---

### STORY-039: Critical Bug Fixes

**Type:** Frontend + Backend
**Priority:** P0 — must complete before any deployment testing
**Estimated effort:** 1-2 days

**Scope (all bugs below):**
- BUG-001: Remove double Header/Footer
- BUG-002: Create /dashboard redirect page
- BUG-003: Remove backdrop-blur from Header
- BUG-004: Fix middleware.ts authenticated redirect
- BUG-005: Fix OnboardingWizard redirect to /chat
- BUG-009: Fix Dockerfile.api --reload
- BUG-015: Fix Delete Account API call
- BUG-016: Wire auto-save hook in MetaDocEditor
- BUG-017: Fix MetaDocHistory content loading
- BUG-018: Fix Graph date range filter
- BUG-019: Add ErrorBoundary to dashboard layout
- BUG-020: Add skip link to dashboard layout
- BUG-022: Fix MemoryChat stream reader cleanup
- BUG-023: Fix notification test email endpoint
- BUG-024: Fix data export status URL
- BUG-027: Fix PricingSection dashboard link
- BUG-028: Fix MemoryInbox activeIndex out of bounds
- BUG-032: Add Zod validation to ProfileContext
- BUG-033: Validate checkout URL before redirect

**Acceptance criteria (checkbox list):**
- [ ] Landing page: exactly ONE header, ONE footer
- [ ] /dashboard redirects to /chat (not 404)
- [ ] Scrolled header: solid bg-background (no blur)
- [ ] Logged-in user at / → redirects to /chat
- [ ] Onboarding completion → /chat (not 404)
- [ ] Dockerfile.api has --workers 2 (no --reload)
- [ ] Delete Account fires DELETE /v1/account before showing success
- [ ] Workstation auto-saves to localStorage every 30s
- [ ] Workstation history click loads content_markdown correctly
- [ ] Graph date range filter actually filters nodes
- [ ] Dashboard component crashes show ErrorBoundary (not white screen)
- [ ] Skip link visible on keyboard focus in dashboard
- [ ] MemoryChat stream reader cancelled on unmount
- [ ] Notification test email uses correct endpoint
- [ ] Data export status uses correct URL pattern
- [ ] PricingSection "Open dashboard" links to /chat
- [ ] MemoryInbox resolving last conflict shows ALL_CLEAR (no crash)
- [ ] ProfileContext validates API responses with Zod
- [ ] Checkout URL validated before window.location.href redirect

---

### STORY-040: Admin Bypass System

**Type:** Cross-repo (Backend + Frontend)
**Priority:** P0 — must complete before any feature testing
**DEPENDS ON:** STORY-039 (env setup)

**Scope:**
- ADMIN-001: Backend CreditService admin bypass
- ADMIN-002: GET /v1/me is_admin field
- ADMIN-003: Frontend Sidebar admin indicator
- ADMIN-004: Frontend Pricing page admin view
- BUG-006: No admin bypass (same as ADMIN-001)
- BUG-011: Set real ADMIN_USER_IDS in .env files

**Acceptance criteria:**
- [ ] Admin user generates Meta-Doc → 0 credits deducted
- [ ] Admin user sends chat → 0 credits deducted
- [ ] Admin user uploads file → 0 credits deducted
- [ ] credit_transactions table has rows with operation="admin_bypass:*"
- [ ] GET /v1/me returns {is_admin: true} for admin user
- [ ] Sidebar shows "◆ ADMIN_ACCESS" for admin user
- [ ] Pricing page shows "Admin Account" message for admin user (no tier cards)
- [ ] ADMIN_USER_IDS set in both repos' env files with real Clerk user ID

---

### STORY-041: Sources Page Upload + UX Gaps + Deployment Config

**Type:** Frontend
**Priority:** P1 — must complete before production launch
**DEPENDS ON:** STORY-039

**Scope:**
- UX-001: Wire IngestionDropzone into Sources page
- UX-002: Verify dark mode toggle
- UX-003: Verify HeroSection dual CTA
- BUG-010: Create vercel.json
- BUG-014: Remove fake testimonials
- BUG-021: Remove /search and /generate from Omnibar command list
- BUG-025: GraphQueryBar example auto-execute
- BUG-026: Admin stats progress bar fix
- BUG-029: Profile color selector CSS var fix
- BUG-030: Remove duplicate color in COLOR_OPTIONS
- BUG-031: Fix loading skeletons
- DEPLOY-001: Create vercel.json
- DEPLOY-002: Fix next.config.mjs

**Acceptance criteria:**
- [ ] /sources Upload tab shows IngestionDropzone (not "coming soon")
- [ ] Dark mode toggle writes .dark to document.documentElement
- [ ] HeroSection has two CTAs: primary "Start for free" + secondary "How it works"
- [ ] vercel.json created with security headers
- [ ] next.config.mjs has correct remotePatterns
- [ ] Testimonials section removed (or replaced with real testimonials)
- [ ] Omnibar shows only /ingest and /profile (no unimplemented commands)
- [ ] npm run build → 0 TypeScript errors

---

### STORY-042: Production Deployment

**Type:** DevOps
**Priority:** P0 (final step)
**DEPENDS ON:** STORY-039, STORY-040, STORY-041, all accounts created

**Scope:**
- Follow PART 6 (Railway) + PART 7 (Vercel) deployment guides exactly
- Run smoke tests from PART 9

**Acceptance criteria:**
- [ ] https://api.ravenbase.app/health → {"status": "healthy"}
- [ ] https://ravenbase.app → 200 OK
- [ ] Registration → Onboarding → Chat end-to-end flow works
- [ ] Admin user can use all LLM features without 402 errors
- [ ] Stripe webhook receives events (test with stripe listen)
- [ ] Clerk webhook creates users in DB on registration

---

## PART 9: ENVIRONMENT VARIABLE MASTER LIST

### ravenbase-api (both API and Worker services)

| Variable | Required | Source | Format Example |
|---|---|---|---|
| DATABASE_URL | Yes | Railway PostgreSQL (auto) | postgresql://user:pass@host:5432/db |
| REDIS_URL | Yes | Railway Redis (auto) | redis://default:pass@host:6379 |
| QDRANT_URL | Yes | Qdrant Cloud dashboard | https://xxx.qdrant.io |
| QDRANT_API_KEY | Yes | Qdrant Cloud → API Keys | qdrant_abc123... |
| NEO4J_URI | Yes | AuraDB instance | neo4j+s://xxx.databases.neo4j.io |
| NEO4J_USER | Yes | AuraDB (always "neo4j") | neo4j |
| NEO4J_PASSWORD | Yes | AuraDB instance creation | complex-password-here |
| OPENAI_API_KEY | Yes | platform.openai.com | sk-proj-... |
| ANTHROPIC_API_KEY | Yes | console.anthropic.com | sk-ant-api03-... |
| GEMINI_API_KEY | Yes | aistudio.google.com | AIzaSy... |
| SUPABASE_URL | Yes | Supabase → Settings → API | https://xxx.supabase.co |
| SUPABASE_SERVICE_ROLE_KEY | Yes | Supabase → Settings → API → service_role | eyJhb... |
| STORAGE_BUCKET | Yes | Must match Supabase bucket name | ravenbase-sources |
| ADMIN_USER_IDS | Yes | Clerk Dashboard → Users | user_2abc,user_2def |
| APP_ENV | Yes | Manual | production |
| ENABLE_PII_MASKING | Yes | Manual | true |
| SENTRY_DSN | Optional | sentry.io → Project → DSN | https://xxx@sentry.io/xxx |

### ravenbase-api (API service only)

| Variable | Required | Source | Format Example |
|---|---|---|---|
| CLERK_FRONTEND_API | Yes | Clerk Production → API Keys | your-app.clerk.accounts.dev |
| CLERK_WEBHOOK_SECRET | Yes | Clerk → Webhooks → signing secret | whsec_... |
| STRIPE_SECRET_KEY | Yes | Stripe → Developers → API Keys | sk_live_... |
| STRIPE_WEBHOOK_SECRET | Yes | Stripe → Webhooks → signing secret | whsec_... |
| STRIPE_PRO_MONTHLY_PRICE_ID | Yes | Stripe → Products → Prices | price_... |
| STRIPE_PRO_ANNUAL_PRICE_ID | Yes | Stripe → Products → Prices | price_... |
| STRIPE_TEAM_MONTHLY_PRICE_ID | Yes | Stripe → Products → Prices | price_... |
| STRIPE_TEAM_ANNUAL_PRICE_ID | Yes | Stripe → Products → Prices | price_... |
| APP_BASE_URL | Yes | Your domain | https://ravenbase.app |
| RESEND_API_KEY | Yes | Resend dashboard | re_... |
| RESEND_WEBHOOK_SECRET | Optional | Resend webhooks | whsec_... |

### ravenbase-web (.env.local for dev / Vercel env vars for prod)

| Variable | Required | Source | Format Example |
|---|---|---|---|
| NEXT_PUBLIC_API_URL | Yes | Manual | https://api.ravenbase.app |
| NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY | Yes | Clerk Production | pk_live_... |
| CLERK_SECRET_KEY | Yes | Clerk Production | sk_live_... |
| NEXT_PUBLIC_CLERK_SIGN_IN_URL | Yes | Manual | /login |
| NEXT_PUBLIC_CLERK_SIGN_UP_URL | Yes | Manual | /register |
| NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL | Yes | Manual | /chat |
| NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL | Yes | Manual | /onboarding |
| CLERK_WEBHOOK_SECRET | Yes | Clerk → Webhooks | whsec_... |
| NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY | Yes | Stripe | pk_live_... |
| ADMIN_USER_IDS | Yes | Clerk Dashboard | user_2abc... |

---

## PART 10: DEFINITION OF DONE SMOKE TESTS

All tests below MUST pass before declaring "production ready".
Run in order — earlier tests are prerequisites for later ones.

### Marketing

```
□ https://ravenbase.app — 200 OK, loads in < 3s
□ Landing page: exactly ONE nav bar, ONE footer (no duplicate)
□ Scroll on landing → header is solid (no blur visible)
□ Hero section: TWO CTAs visible
□ /pricing → 3 tier cards rendered, annual/monthly toggle works
□ /pricing → logged-in admin user sees "Admin Account" message (no tier cards)
□ /privacy → renders correctly
□ /terms → renders correctly
□ "How it works" nav link → smooth scrolls to section on /
□ All external links open in new tab
```

### Authentication flow

```
□ /register → Clerk SignUp component renders with Ravenbase branding
□ Create a NEW test account via /register
□ After signup → redirected to /onboarding (not /chat)
□ Complete onboarding (create profile) → redirected to /chat (not /dashboard or 404)
□ /dashboard → 307 redirect to /chat
□ /chat without auth → 307 redirect to /login
□ Already logged in → visit / → immediately redirected to /chat
```

### Dashboard navigation

```
□ /chat renders with input + empty state
□ /inbox renders with empty state OR conflict cards
□ /graph renders with empty state OR graph
□ /sources renders with Sources list + Upload tab (has dropzone, NOT "coming soon")
□ /workstation renders with history panel + editor + prompt input
□ /settings/profile → profile settings form renders
□ /settings/billing → billing page renders
□ /settings/data → data/privacy page renders (Delete Account button present)
□ All sidebar links navigate correctly
□ Cmd+K (Mac) opens Omnibar
□ Omnibar: only /ingest and /profile shown (no unimplemented commands)
```

### Admin bypass (requires admin user)

```
□ Sidebar shows "◆ ADMIN_ACCESS" (not credit count)
□ /pricing shows "Admin Account" message (not tier cards)
□ Generate Meta-Doc → completes successfully → credit balance unchanged
□ Send Chat message → responds successfully → credit balance unchanged
□ credit_transactions table has rows with operation="admin_bypass:*"
```

### Core features (requires backend running + ingested data)

```
□ Omnibar /ingest "Hello test" → toast "Captured to [Profile]" → 0 credits deducted
□ Upload a PDF at /sources → status progresses to "completed" within 60s
□ /graph shows nodes after ingestion
□ Ingest two contradictory texts → /inbox shows conflict card within 60s
□ Resolve conflict with Enter → card animates out → count decrements
□ Generate Meta-Doc at /workstation → tokens stream → "◆ SAVED_JUST_NOW" after done
□ Click history item → document content loads (not empty)
□ Export Meta-Doc → .md file downloads with correct content
□ Chat message → response streams → citation cards appear after done
```

### Settings and privacy

```
□ Delete Account: type "DELETE" → confirm → fires DELETE /v1/account → redirect to /
□ Data export: click Export → 202 response received → toast shown
□ Profile creation → new profile appears in Omnibar /profile list
□ Profile color selector → color renders correctly (no blank squares)
```

### Performance and accessibility

```
□ Tab through landing page → all interactive elements focusable in logical order
□ Tab through dashboard → skip link visible on first Tab press → jumps to main content
□ Streaming SSE content in /chat and /workstation is in aria-live region
□ Dark mode toggle → .dark class on <html> element → colors update globally
□ Mobile (375px viewport): sidebar hidden → hamburger or sheet trigger present
□ Mobile (375px): /chat → input sticky at bottom, safe area padding applied
```

### Production health

```
□ https://api.ravenbase.app/health → {"status": "healthy", "postgres": "ok", "redis": "ok"}
□ https://api.ravenbase.app/v1/conflicts → 401 (not 404, not 500)
□ POST https://api.ravenbase.app/webhooks/clerk → 400 (missing signature, not 404)
□ POST https://api.ravenbase.app/webhooks/stripe → 400 (missing signature, not 404)
□ curl -I https://ravenbase.app → includes X-Frame-Options: DENY header
□ curl -I https://ravenbase.app → includes X-Content-Type-Options: nosniff header
```
