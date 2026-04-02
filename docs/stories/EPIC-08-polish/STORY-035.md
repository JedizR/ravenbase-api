# STORY-035: Data Export / Right to Portability

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-024 (same multi-store pattern), STORY-032 (email service)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — data export / right to portability story.

## Component
COMP-07: PrivacyLayer

---

> **Before You Start — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (3-layer, ARQ, structlog)
> 2. `docs/architecture/02-database-schema.md` — all models being exported
> 3. `docs/stories/EPIC-08-polish/STORY-024.md` — GDPR deletion (same multi-store approach)
> 4. `docs/stories/EPIC-08-polish/STORY-032.md` — email service (send completion email)

---

## User Story
As a user, I want to download all my Ravenbase data in a portable format so I can
take my knowledge graph elsewhere or simply have a backup.

## Context
- GDPR Article 20 (Right to Data Portability) for EU users
- Export is async ARQ job — files can be very large
- Completion notification via Resend email
- Download link = pre-signed Supabase Storage URL (72-hour expiry)
- Rate limited: 1 export per 24 hours per user

## Acceptance Criteria
- [ ] AC-1: `POST /v1/account/export` returns `202` with `job_id` and enqueues ARQ task
- [ ] AC-2: Rate limit: second request within 24h returns `429` with `retry_after_seconds`
- [ ] AC-3: ARQ task collects: original source files, Meta-Documents as `.md`, Neo4j graph as JSON, SystemProfiles as JSON
- [ ] AC-4: All files compressed into ZIP at `exports/{user_id}/{timestamp}.zip` in Supabase Storage
- [ ] AC-5: Pre-signed download URL generated (72-hour expiry)
- [ ] AC-6: Completion email sent via `EmailService` with download link (respects `notify_ingestion_complete` preference)
- [ ] AC-7: `GET /v1/account/export/status` returns current status and URL
- [ ] AC-8: Settings → Data page has "Export my data" button + "last exported" timestamp
- [ ] AC-9: If any single component fails (e.g. Neo4j export errors): log error, skip that component, complete ZIP with `PARTIAL_EXPORT.txt` explaining what was excluded — never fail the whole job
- [ ] AC-10: Export ZIPs auto-deleted from Supabase Storage after 7 days

## Technical Notes

### Files to Create
- `src/workers/tasks/export.py` — `generate_user_export` ARQ task
- `src/services/export_service.py`

### Files to Modify
- `src/api/routes/account.py` — add POST /v1/account/export, GET /v1/account/export/status

### Architecture Constraints
- Filter ALL queries by `tenant_id` — never include other users' data
- Never include raw Qdrant vectors (derived data, not user data per GDPR)
- Partial failures are non-fatal — produce `PARTIAL_EXPORT.txt` not a failed job
- Rate limit via Redis key `export:cooldown:{user_id}` TTL 24h
- Store only `storage_path` in JobStatus (URL is ephemeral, regenerated on status check)
- Export idempotency: if ZIP already exists at `storage_path`, skip recreation (for ARQ retries)

## UX & Visual Quality Requirements

### Settings → Data Page UX
1. Page header:
   - h1: font-serif text-3xl "Your Data"
   - Subtitle: text-sm text-muted-foreground "Download everything you've stored in Ravenbase."
   - Mono label: ◆ DATA_PORTABILITY

2. Format selector (before export button):
   Three format cards side by side (or stacked on mobile):
   - JSON (default): "Complete structured data, machine-readable"
   - CSV: "Spreadsheet-compatible, sources and memories only"
   - ZIP: "Everything including original uploaded files"

   Each card: bg-card rounded-2xl border p-4 cursor-pointer
   Selected: border-2 border-primary bg-primary/5
   Icon per format: File (JSON), Table (CSV), Archive (ZIP) from lucide-react

3. File size estimate below format selector:
   - text-xs font-mono text-muted-foreground
   - Shows: "Estimated size: ~X MB" based on user's source count
   - Fetched from GET /v1/users/me or estimated client-side

4. Export button states:
   - Idle: "◆ EXPORT_DATA" — rounded-full bg-primary text-primary-foreground h-11 w-full
   - Loading: spinner + "Preparing export..."
   - Progress (if large): forest green determinate progress bar (0→100%)
   - Success: "◆ EXPORT_READY" + download link button
   - Error: toast.error("Export failed. Try again or contact support.")
   - Rate limited: toast.error("Export already in progress. Try again in X minutes.")

5. Success state after export:
   - Green checkmark animation (SVG check-draw from globals.css)
   - "Your data is ready" heading in font-serif
   - "Download expires in 24 hours" in text-xs text-muted-foreground
   - Download button: rounded-full bg-success text-success-foreground

6. "Delete all data" section (GDPR):
   - Separated from export section by <Separator />
   - Section header: ◆ DANGER_ZONE in text-destructive mono
   - "Delete my account and all data" button:
     rounded-full border border-destructive text-destructive
     hover:bg-destructive hover:text-destructive-foreground
   - Opens AlertDialog (not inline) with:
     - Warning: "This permanently deletes your account, knowledge graph,
       and all uploaded files. This cannot be undone."
     - Confirmation input: user must type "DELETE" before button enables
     - Delete button: rounded-full bg-destructive text-destructive-foreground

## Definition of Done
- [ ] `POST /v1/account/export` returns 202 with job_id
- [ ] ZIP created in Supabase Storage with all 4 components
- [ ] Partial failures produce PARTIAL_EXPORT.txt (job does not fail)
- [ ] Email sent with download link
- [ ] Rate limit enforced (24h cooldown)
- [ ] `make quality && make test` passes

## Final Localhost Verification (mandatory before marking complete)

After `make quality && make test` passes, verify the running application works:

**Step 1 — Start dev server:**
```bash
cd ravenbase-api && make run
```

**Step 2 — Verify no runtime errors:**
- Test the export endpoint with curl or a tool like Postman
- Confirm no unhandled exceptions in server logs
- Confirm structlog output is clean

**Step 3 — Report one of:**
- ✅ `localhost verified` — export service runs correctly
- ⚠️ `Issue found: [describe issue]` — fix before committing docs

Only commit the docs update (epics.md, story-counter, project-status, journal) AFTER localhost verification passes.

## Testing This Story

```bash
# Test data export flow end-to-end:
# 1. POST /v1/account/export → expect 202 with job_id
# 2. Poll GET /v1/account/export/status until status = "completed"
# 3. Verify download_url is a Supabase pre-signed URL (contains "supabase.co")
# 4. Download the ZIP and verify it contains:
#    - sources/ directory (original uploaded files)
#    - meta_documents/ directory (.md files)
#    - graph_export.json
#    - profiles.json
#    - README.txt
# 5. POST /v1/account/export again immediately → expect 429 with retry_after_seconds
# 6. Verify export ZIP contains ONLY this user's data (check no other tenant_id present)
# 7. Partial failure test: mock Neo4j adapter to raise an exception → verify job still
#    completes with PARTIAL_EXPORT.txt listing "Knowledge Graph: <error message>"
# 8. Verify download_url expires after 72 hours (check Supabase signed URL expiry param)
```

## Frontend Agent Brief

> **Skill Invocations — invoke each skill before the corresponding phase:**
>
> **Phase 1 (Read/Design):** `Use /frontend-design — enforce production-grade aesthetic compliance`
> **Phase 2 (Components):** `Use /tailwindcss — for Tailwind CSS v4 token system`
> **Phase 3 (State Management):** `Use /tailwindcss-animations — for loading/progress animations`
> **Phase 4 (Mobile):** `Use /tailwindcss-mobile-first — for responsive layout verification`
> **Phase 5 (Verification):** `Use /superpowers:verification-before-completion — before claiming done`

---

```
🎯 Target: Claude Code / MiniMax-M2.7 — Ultra-detailed planning and implementation
💡 Optimization: MiniMax-M2.7 directive — WRITE EVERYTHING IN MAXIMUM DETAIL.
   Plans MUST be 1500-3000 lines. Never short-circuit with "see code below".

═══════════════════════════════════════════════════════════════════
STEP 0 — PROJECT CONTEXT (carry forward to every phase)
═══════════════════════════════════════════════════════════════════

Ravenbase Frontend: Next.js 15 App Router + Tailwind CSS v4 + shadcn/ui + TanStack Query
Design system: CSS variables only (no hardcoded hex). Dark mode via .dark class on <html>
Brand colors: Primary=#2d4a3e (forest green), Background=#f5f3ee (warm cream), Accent=#a8c4b2
DO NOT introduce new design aesthetics — follow the established brand system exactly.
Page directory: app/(dashboard)/settings/data/page.tsx (already exists)
Page loading: app/(dashboard)/settings/data/loading.tsx (already exists)

API endpoints:
- POST /v1/account/export → { job_id: string } (returns 202 on success, 429 if rate limited)
- GET /v1/account/export/status?job_id={job_id} → ExportStatus

Backend must be complete first:
grep -n "export" ravenbase-api/src/api/routes/account.py | head -20

═══════════════════════════════════════════════════════════════════
STEP 1 — READ PHASE (mandatory — read ALL files before touching code)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /frontend-design

Read ALL files in order — NOT in parallel — every file completely:

1. CLAUDE.md
   → All 19 rules. Critical rules for this story:
     RULE 1: No <form> tags — use onClick + controlled state
     RULE 2: All styling via Tailwind classes only (no inline styles)
     RULE 3: All API calls via apiFetch() from lib/api.ts (client) or lib/api-client.ts (server component)
     RULE 6: TanStack Query for all server state (useQuery/useMutation)
     RULE 7: shadcn/ui for all base components
     RULE 11: Touch targets at least 44px tall on mobile
     RULE 18: Form fields validate on blur with 300ms debounce

2. docs/design/AGENT_DESIGN_PREAMBLE.md
   → Anti-patterns to reject on sight:
     ❌ className="rounded-lg" on cards → must be rounded-2xl
     ❌ className="rounded-md" on CTAs → must be rounded-full
     ❌ bg-[#2d4a3e] → must be bg-primary
     ❌ bg-[#f5f3ee] → must be bg-background
     ❌ floating labels / inline placeholder-as-label
     ❌ gradient buttons → solid bg-primary only

3. docs/design/00-brand-identity.md
   → Mono label pattern: ◆ DATA_PORTABILITY, ◆ DANGER_ZONE
   → Brand voice: precise, active, direct — no corporate fluff
   → Success state: "Your data is ready" not "Woohoo!"

4. docs/design/01-design-system.md
   → All CSS variable definitions (light and dark)
   → Card style: bg-card rounded-2xl border border-border
   → CTA: rounded-full bg-primary text-primary-foreground
   → Section mono label: text-xs font-mono text-muted-foreground tracking-wider
   → Success color: text-success (#3d8b5a) / bg-success
   → Destructive: text-destructive (#b53233) / bg-destructive
   → Warning: bg-warning (#ffc00d) with text-[var(--warning-foreground)]

5. docs/design/04-ux-patterns.md
   → Progress indicators: determinate bar with percentage (Section 6)
   → Button loading state pattern: disable + change text while in flight
   → Label pairs: "Export" → "Exporting…" (Section 5)
   → Destructive action pattern: AlertDialog + typed confirmation for GDPR delete
   → sonner toast for all error/success notifications

6. docs/stories/EPIC-08-polish/STORY-035.md (this file)
   → All ACs. Frontend: AC-8, AC-9, AC-10. Backend: AC-1 through AC-7.
   → CONFIRMED: Read every acceptance criterion

═══════════════════════════════════════════════════════════════════
STEP 2 — API CONTRACT (Phase 1a — document before writing code)
═══════════════════════════════════════════════════════════════════

POST /v1/account/export
Request body: { "format": "json" | "csv" | "zip" }
Success response (202): { "job_id": string, "status": "queued" }
Rate limited response (429): { "detail": { "code": "EXPORT_RATE_LIMITED", "retry_after_seconds": number } }
Error response (4xx/5xx): { "detail": { "code": string, "message": string } }

GET /v1/account/export/status?job_id={job_id}
Response: {
  "status": "idle" | "queued" | "preparing" | "ready" | "failed",
  "job_id": string,
  "download_url": string | null,  // present when status = "ready"
  "progress": number,             // 0-100
  "error": string | null          // present when status = "failed"
}

═══════════════════════════════════════════════════════════════════
STEP 3 — PAGE DESIGN (Phase 2a — full code for page.tsx)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss

FILE: app/(dashboard)/settings/data/page.tsx

This file ALREADY EXISTS. You are enhancing it to match this exact specification.
Key fixes from existing version:
1. Import useApiFetch from @/lib/api-client (not @/lib/api)
2. Export mutation onError must handle 429 rate limit specifically
3. Export status query: use jobId stored in mutation state, not queryClient.getQueryData
4. The enabled flag must correctly gate polling

Complete code — every line, no omissions:

```tsx
"use client"
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Download,
  Loader2,
  CheckCircle2,
  FileText,
  Table,
  Archive,
} from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"
import { useApiFetch } from "@/lib/api-client"

interface ExportStatus {
  status: "idle" | "queued" | "preparing" | "ready" | "failed"
  job_id: string
  download_url: string | null
  progress: number
  error: string | null
}

const formats = [
  {
    id: "json" as const,
    label: "JSON",
    description: "Complete structured data, machine-readable",
    icon: FileText,
  },
  {
    id: "csv" as const,
    label: "CSV",
    description: "Spreadsheet-compatible, sources and memories only",
    icon: Table,
  },
  {
    id: "zip" as const,
    label: "ZIP",
    description: "Everything including original uploaded files",
    icon: Archive,
  },
]

export default function DataSettingsPage() {
  const [selectedFormat, setSelectedFormat] = useState<"json" | "csv" | "zip">("json")
  const [confirmText, setConfirmText] = useState("")
  const queryClient = useQueryClient()
  const apiFetch = useApiFetch()

  // Export mutation — triggers POST /v1/account/export
  const exportMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ job_id: string }>("/v1/account/export", {
        method: "POST",
        body: JSON.stringify({ format: selectedFormat }),
      }),
    onSuccess: (data) => {
      // Store job_id so the status query can poll it
      queryClient.setQueryData(["export-job-id"], data)
      queryClient.setQueryData(["export-status"], {
        status: "queued",
        job_id: data.job_id,
        download_url: null,
        progress: 0,
        error: null,
      } as ExportStatus)
      toast.success("Export started. We'll email you when it's ready.")
    },
    onError: (error: Error & { response?: { status?: number; data?: { detail?: { code?: string; message?: string; retry_after_seconds?: number } } } }) => {
      // AC-2: Handle rate limit (429) specifically
      if (error?.response?.status === 429) {
        const retryAfter = error.response.data?.detail?.retry_after_seconds
        const minutes = retryAfter ? Math.ceil(retryAfter / 60) : 60
        toast.error(
          `Export already in progress. Try again in ${minutes} minute${minutes !== 1 ? "s" : ""}.`
        )
        return
      }
      toast.error("Export failed. Please try again or contact support.")
    },
  })

  // Poll export status — enabled only when we have a job_id
  const { data: exportStatus } = useQuery<ExportStatus>({
    queryKey: ["export-status"],
    queryFn: async () => {
      const jobData = queryClient.getQueryData<{ job_id: string }>(["export-job-id"])
      if (!jobData?.job_id) throw new Error("No job ID")
      return apiFetch<ExportStatus>(
        `/v1/account/export/status?job_id=${jobData.job_id}`
      )
    },
    enabled: !!queryClient.getQueryData<{ job_id: string }>(["export-job-id"])?.job_id,
    refetchInterval: (q) => {
      const status = q.state.data?.status
      // Stop polling when export is complete or failed
      return status === "ready" || status === "failed" ? false : 3000
    },
  })

  const isExporting =
    exportStatus?.status === "queued" || exportStatus?.status === "preparing"
  const canDownload = exportStatus?.status === "ready"
  const hasFailed = exportStatus?.status === "failed"
  const progress = exportStatus?.progress ?? 0
  const downloadUrl = exportStatus?.download_url ?? null

  const handleDeleteAccount = async () => {
    // Backend handles full deletion flow including email confirmation
    toast.success("Account deletion initiated. You'll receive a confirmation email.")
    setConfirmText("")
  }

  return (
    <div className="space-y-8 max-w-2xl">
      {/* Export section */}
      <section>
        <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
          ◆ DATA_PORTABILITY
        </p>
        <h1 className="font-serif text-3xl mb-2">Your Data</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Download everything you have stored in Ravenbase.
        </p>

        {/* Format selector — 3 cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          {formats.map((f) => {
            const Icon = f.icon
            const isSelected = selectedFormat === f.id
            return (
              <button
                key={f.id}
                onClick={() => setSelectedFormat(f.id)}
                aria-pressed={isSelected}
                className={`
                  bg-card rounded-2xl border p-4 text-left cursor-pointer
                  transition-all hover:shadow-md
                  ${isSelected
                    ? "border-2 border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
                  }
                `}
              >
                <Icon className={`w-5 h-5 mb-2 ${isSelected ? "text-primary" : "text-muted-foreground"}`} />
                <p className="font-medium text-sm mb-1">{f.label}</p>
                <p className="text-xs text-muted-foreground">{f.description}</p>
              </button>
            )
          })}
        </div>

        {/* EXPORT BUTTON STATES */}
        {/* State 1: Idle — show export button */}
        {(!exportStatus || exportStatus.status === "idle") && (
          <button
            onClick={() => exportMutation.mutate()}
            disabled={exportMutation.isPending}
            className="w-full h-11 rounded-full bg-primary text-primary-foreground
                       font-medium flex items-center justify-center gap-2
                       disabled:opacity-50 transition-colors"
          >
            <Download className="w-4 h-4" />
            ◆ EXPORT_DATA
          </button>
        )}

        {/* State 2: Loading — show spinner with "Preparing export..." */}
        {exportMutation.isPending && (
          <button
            disabled
            className="w-full h-11 rounded-full bg-primary text-primary-foreground
                       font-medium flex items-center justify-center gap-2
                       opacity-70"
          >
            <Loader2 className="w-4 h-4 animate-spin" />
            Preparing export...
          </button>
        )}

        {/* State 3: Exporting — show progress bar */}
        {isExporting && (
          <div className="space-y-2">
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground text-center">
              Preparing export... {progress}%
            </p>
          </div>
        )}

        {/* State 4: Download ready */}
        {canDownload && downloadUrl && (
          <div className="bg-card rounded-2xl border border-border p-6 space-y-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-success" />
              <p className="font-serif text-lg">Your data is ready</p>
            </div>
            <p className="text-xs font-mono text-muted-foreground">
              Download expires in 24 hours
            </p>
            <a
              href={downloadUrl}
              download
              className="w-full h-11 rounded-full bg-success text-success-foreground
                         font-medium flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download ZIP
            </a>
          </div>
        )}

        {/* State 5: Failed */}
        {hasFailed && (
          <div className="bg-destructive/10 border border-destructive/25 rounded-2xl p-4">
            <p className="text-sm text-destructive">
              Export failed: {exportStatus.error ?? "Unknown error"}. Please try again or contact support.
            </p>
            <button
              onClick={() => {
                queryClient.setQueryData(["export-job-id"], null)
                queryClient.setQueryData(["export-status"], null)
              }}
              className="mt-2 text-xs text-destructive underline"
            >
              Dismiss
            </button>
          </div>
        )}
      </section>

      {/* Danger zone — DELETE ACCOUNT (GDPR) */}
      <Separator />
      <section>
        <p className="text-xs font-mono text-destructive tracking-wider mb-2">
          ◆ DANGER_ZONE
        </p>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <button className="w-full h-11 rounded-full border border-destructive
                               text-destructive font-medium
                               hover:bg-destructive hover:text-destructive-foreground
                               transition-colors">
              Delete my account and all data
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent className="rounded-2xl">
            <AlertDialogHeader>
              <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              <AlertDialogDescription>
                This permanently deletes your account, knowledge graph,
                and all uploaded files. This cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>

            {/* AC-10: Confirmation input — user must type "DELETE" */}
            <div className="space-y-2">
              <label htmlFor="delete-confirm" className="text-sm font-medium">
                Type{" "}
                <span className="font-mono text-destructive">DELETE</span>{" "}
                to confirm
              </label>
              <Input
                id="delete-confirm"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="DELETE"
                autoComplete="off"
                className={
                  confirmText === "DELETE"
                    ? "border-success focus:border-success"
                    : ""
                }
              />
            </div>

            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => setConfirmText("")}>
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDeleteAccount}
                disabled={confirmText !== "DELETE"}
                className="bg-destructive text-destructive-foreground
                           hover:bg-destructive/90 disabled:opacity-50"
              >
                Delete my account
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </section>
    </div>
  )
}
```

═══════════════════════════════════════════════════════════════════
STEP 4 — LOADING STATE (Phase 2b — required by RULE 10)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-mobile-first

FILE: app/(dashboard)/settings/data/loading.tsx

This file ALREADY EXISTS. Verify it matches this exact specification.

```tsx
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"

export default function DataSettingsLoading() {
  return (
    <div className="space-y-8 max-w-2xl">
      {/* Page header skeleton */}
      <div>
        <Skeleton className="h-4 w-32 mb-2" />
        <Skeleton className="h-8 w-48 mb-2" />
        <Skeleton className="h-4 w-full max-w-md" />
      </div>

      {/* Format selector skeleton — 3 cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-2xl" />
        ))}
      </div>

      {/* Export button skeleton */}
      <Skeleton className="h-11 w-full rounded-full" />

      {/* Separator + Danger zone skeleton */}
      <Separator />
      <div>
        <Skeleton className="h-4 w-32 mb-2" />
        <Skeleton className="h-11 w-full rounded-full" />
      </div>
    </div>
  )
}
```

RULE 10: Every dashboard page must have a loading.tsx sibling.
This skeleton renders during navigation while data fetches.

═══════════════════════════════════════════════════════════════════
STEP 5 — VERIFICATION COMMANDS (Phase 3)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-animations

Run these exact grep commands and verify the expected counts:

# 1. Page header — mono label ◆ DATA_PORTABILITY
grep -c "◆ DATA_PORTABILITY" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 2. Format selector — 3 cards with border-2 border-primary when selected
grep -c "border-2 border-primary" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 3. Format selector — 3 cards, rounded-2xl
grep -c "rounded-2xl" app/\(dashboard\)/settings/data/page.tsx
Expected: At least 2 (format cards + download success card)

# 4. Export button — "◆ EXPORT_DATA" rounded-full bg-primary
grep -c '◆ EXPORT_DATA' app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 5. Loading spinner — Loader2 animate-spin
grep -c 'Loader2.*animate-spin' app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 6. Progress bar — bg-primary rounded-full
grep -c "bg-primary.*rounded-full" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 7. Success state — CheckCircle2 text-success
grep -c "CheckCircle2.*text-success" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 8. Download link — download attribute on <a> tag
grep -c 'download' app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 9. Success state — "Download expires in 24 hours"
grep -c "Download expires in 24 hours" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 10. Danger zone — mono label ◆ DANGER_ZONE
grep -c "◆ DANGER_ZONE" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 11. AlertDialog with DELETE confirmation input
grep -c 'placeholder="DELETE"' app/\(dashboard\)/settings/data/page.tsx
Expected: 1
grep -c 'value={confirmText}' app/\(dashboard\)/settings/data/page.tsx
Expected: 1
grep -c 'disabled={confirmText !== "DELETE"}' app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 12. TanStack Query — useMutation for export
grep -c "useMutation" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 13. TanStack Query — useQuery for status polling
grep -c "useQuery.*ExportStatus" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 14. Polling — refetchInterval stops when ready or failed
grep -c "status.*ready.*false.*failed" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 15. Rate limit handling — 429 status check in onError
grep -c "429\|EXPORT_RATE_LIMITED" app/\(dashboard\)/settings/data/page.tsx
Expected: At least 1

# 16. Toast for rate limit — "Try again in X minutes"
grep -c "Try again in" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 17. useApiFetch import
grep -c 'useApiFetch' app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 18. Loading state exists
ls app/\(dashboard\)/settings/data/loading.tsx 2>/dev/null && echo "EXISTS" || echo "MISSING"
Expected: EXISTS

# 19. No <form> tags (RULE 1: never use form tags)
grep -c "<form" app/\(dashboard\)/settings/data/page.tsx
Expected: 0

# 20. No hardcoded hex colors
grep -c "#2d4a3e\|#f5f3ee\|#ffc00d" app/\(dashboard\)/settings/data/page.tsx
Expected: 0

# 21. TanStack Query refetchInterval — 3000ms polling
grep -c "refetchInterval.*3000" app/\(dashboard\)/settings/data/page.tsx
Expected: 1

# 22. Export button disabled while mutation is pending
grep -c 'disabled={exportMutation.isPending}' app/\(dashboard\)/settings/data/page.tsx
Expected: 1

═══════════════════════════════════════════════════════════════════
STEP 6 — AC-BY-AC VERIFICATION
═══════════════════════════════════════════════════════════════════

For each acceptance criterion, write a one-line verification result:

□ AC-1 (backend): POST /v1/account/export returns 202 with job_id
  VERIFIED: curl -s -X POST http://localhost:8000/v1/account/export \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"format":"json"}' | python -m json.tool
  Expected: {"job_id": "...", "status": "queued"}

□ AC-2 (backend): Rate limit returns 429 with retry_after_seconds
  VERIFIED: Run export twice in quick succession, second request should return 429

□ AC-3 (backend): ARQ task collects sources, meta_docs, graph, profiles
  VERIFIED: grep -n "sources/\|meta_documents/\|graph_export\|profiles" \
    ravenbase-api/src/workers/tasks/export.py

□ AC-4 (backend): ZIP created at exports/{user_id}/{timestamp}.zip
  VERIFIED: Check Supabase Storage bucket after export completes

□ AC-5 (backend): Pre-signed download URL with 72-hour expiry
  VERIFIED: Check URL in status response contains supabase.co and expiry param

□ AC-6 (backend): Completion email sent via EmailService
  VERIFIED: grep -n "EmailService\|send.*export" ravenbase-api/src/services/

□ AC-7 (backend): GET /v1/account/export/status returns status and URL
  VERIFIED: curl "http://localhost:8000/v1/account/export/status?job_id=$JOB_ID" \
    -H "Authorization: Bearer $TOKEN" | python -m json.tool

□ AC-8 (frontend): Settings → Data page with export button
  VERIFIED: grep -c "◆ EXPORT_DATA" app/\(dashboard\)/settings/data/page.tsx = 1
  VERIFIED: grep -c "◆ DATA_PORTABILITY" app/\(dashboard\)/settings/data/page.tsx = 1

□ AC-9 (frontend): Format selector cards
  VERIFIED: grep -c "border-2 border-primary" app/\(dashboard\)/settings/data/page.tsx = 1

□ AC-10 (frontend): AlertDialog requires "DELETE" typed before delete enables
  VERIFIED: grep -c 'placeholder="DELETE"' app/\(dashboard\)/settings/data/page.tsx = 1
  VERIFIED: grep -c 'disabled={confirmText !== "DELETE"}' app/\(dashboard\)/settings/data/page.tsx = 1

═══════════════════════════════════════════════════════════════════
ANTI-PATTERNS — automatic rejection (reject on sight)
═══════════════════════════════════════════════════════════════════

❌ className="rounded-lg" on any card → must be rounded-2xl
❌ className="rounded-md" on any CTA button → must be rounded-full
❌ <form> tag anywhere → RULE 1: use onClick + controlled state, never <form>
❌ Hardcoded hex color (#2d4a3e, #f5f3ee, #ffc00d) → use CSS variable token
❌ floating labels / placeholder-as-label → labels always ABOVE input
❌ DELETE account button without typed confirmation input → AC-10 requires "DELETE"
❌ Delete button enabled when confirmText !== "DELETE" → must be disabled
❌ Progress bar without percentage text → both bar AND text required
❌ Export button not disabled while mutation is pending
❌ No 429 rate limit handling in onError → must show "Try again in X minutes"
❌ TanStack useState + useEffect for API data → RULE 6: use useQuery/useMutation
❌ No loading.tsx sibling → RULE 10: every async dashboard page needs loading.tsx
❌ bg-[#xxxx] anywhere → must use CSS variable token
❌ Gradient buttons → solid bg-primary only

═══════════════════════════════════════════════════════════════════
SUCCESS CRITERIA — ALL must be YES to report complete
═══════════════════════════════════════════════════════════════════

INVOKE: Use /superpowers:verification-before-completion

✅ Page header: ◆ DATA_PORTABILITY + font-serif h1 "Your Data"
✅ Format selector: 3 cards (JSON/CSV/ZIP), selected has border-2 border-primary bg-primary/5
✅ Export button: "◆ EXPORT_DATA" rounded-full bg-primary text-primary-foreground
✅ Export button disabled while isPending (prevents double-submit)
✅ Loading state: Loader2 animate-spin + "Preparing export..." text
✅ Progress bar: bg-primary rounded-full fill with percentage text
✅ Success state: CheckCircle2 text-success + "Your data is ready" + download link
✅ Success state: "Download expires in 24 hours" in text-xs font-mono text-muted-foreground
✅ Error state: toast.error("Export failed. Please try again or contact support.")
✅ Rate limit state: toast.error("Export already in progress. Try again in X minutes.")
✅ Download button: bg-success text-success-foreground rounded-full
✅ Danger zone: ◆ DANGER_ZONE in text-destructive mono label
✅ AlertDialog: requires "DELETE" typed before button enables
✅ Delete button: disabled unless confirmText === "DELETE"
✅ loading.tsx sibling exists matching page structure
✅ TanStack Query: useMutation for export trigger, useQuery for status polling
✅ Polling stops when status = "ready" or "failed"
✅ No <form> tags in the page
✅ No hardcoded hex colors in className strings
✅ All cards use rounded-2xl (not rounded-lg)
✅ npm run build passes (0 TypeScript errors)

Show plan first. Do not implement yet.
```

---

## Development Loop
Follow `docs/DEVELOPMENT_LOOP.md`.
```bash
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-035 data export and portability"
```
