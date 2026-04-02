# OnboardingWizard

> **Component ID:** FE-COMP-03
> **Epic:** EPIC-06 — Authentication & System Profiles
> **Stories:** STORY-019
> **Type:** Frontend (Auth — NOT Dashboard)

---

## ⚠️ CRITICAL ROUTE LOCATION

```
CORRECT:   app/(auth)/onboarding/page.tsx
WRONG:     app/(dashboard)/onboarding/page.tsx  ← Does NOT exist
```

Onboarding has **NO sidebar, NO DashboardHeader**. It is a standalone full-screen experience.
`middleware.ts` includes `/onboarding(.*)` as a public route — accessible immediately after Clerk registration before the user has any profile data.

---

## Purpose

The Onboarding Wizard is the first experience for new Ravenbase users after completing Clerk registration. It guides users through creating their first System Profile and optionally uploading their first file. After onboarding, users are redirected to `/chat` (NOT `/dashboard` — BUG-005 fix required).

---

## User Journey

1. New user completes registration at `/register`
2. Clerk `afterSignUpUrl="/onboarding"` (set as component prop in `app/(auth)/register/[[...rest]]/page.tsx`) — this OVERRIDES the env var `NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL`
3. Clerk creates user → webhook fires → backend creates `User` record + 500 free credits
4. User lands on `/onboarding`
5. **Step 1: Profile Name**
   - Enter profile name (required, min 2 chars)
   - Blur + 300ms debounce validation (RULE-18)
   - Click "Continue" → `POST /v1/profiles {name, is_default: true}`
   - Profile created with UUID
6. **Step 2: Optional File Upload**
   - `react-dropzone` drop zone for PDF/DOCX (max 50MB)
   - Drop/select file → `POST /v1/ingest/upload (multipart: file + profile_id)`
   - Returns `{job_id, source_id}`
   - Show SSE progress via `GET /v1/ingest/stream/{source_id}?token=`
   - "Skip for now →" link available at any time
7. **Completion:** `router.push("/chat")` ← **NOT `/dashboard`** (BUG-005 fixes this)

**Admin user shortcut:**
- Admin users see "Skip Onboarding" as primary option above wizard steps
- Still requires at minimum one profile (all features need profile_id scope)
- Quick path: pre-named "Default" profile created in one click

---

## Subcomponents

```
app/(auth)/onboarding/
  page.tsx                — Orchestrates wizard steps (NO sidebar layout)
  loading.tsx             — Skeleton loading state

components/domain/
  OnboardingWizard.tsx    — Multi-step wizard container (BUG-005 is HERE)
  ProfileNameStep.tsx     — Step 1: profile name input with blur validation
  FileUploadStep.tsx      — Step 2: optional file upload via react-dropzone
  IngestionProgress.tsx   — SSE progress bar for uploaded file
  OnboardingComplete.tsx  — Completion state before redirect to /chat
```

---

## API Contracts

```
POST /v1/profiles
  Request:  { name: string, description?: string, is_default: true }
  Response: { id: string, name: string, is_default: boolean }
  Auth:     Required
  Called:   Step 1 on "Continue"

POST /v1/ingest/upload
  Request:  multipart/form-data { file, profile_id, filename? }
  Response: { job_id: string, source_id: string }
  Auth:     Required
  Called:   Step 2 on file drop/select

GET /v1/ingest/stream/{source_id}?token={clerk_jwt}
  Type:     SSE (text/event-stream)
  Events:   { progress_pct: 0-100, message: string, status: "active"|"completed"|"failed" }
  Note:     token as query param — EventSource API cannot set custom headers
  Called:   After upload to show progress
```

---

## Admin Bypass

Admin users can test all features without completing full onboarding. Show above wizard:

```tsx
{user?.is_admin && (
  <div className="mb-6 p-4 bg-secondary rounded-2xl border border-border">
    <p className="font-mono text-xs text-muted-foreground">◆ ADMIN_ACCESS</p>
    <p className="text-sm mt-1">Create a "Default" profile and skip to the app immediately.</p>
    <Button
      className="mt-3 rounded-full w-full"
      onClick={async () => {
        await apiFetch("/v1/profiles", { method: "POST", body: JSON.stringify({ name: "Default", is_default: true }) })
        router.push("/chat")
      }}
    >
      Quick Setup →
    </Button>
  </div>
)}
```

---

## Design System Rules

Cross-reference: `docs/design/AGENT_DESIGN_PREAMBLE.md` (READ FIRST)

Specific rules:
- **Background:** `bg-background` (`#f5f3ee`) — full-page cream, no sidebar
- **Wizard container:** `max-w-md mx-auto` — centered on page
- **Headlines:** `font-serif text-3xl` (Playfair Display) for "Welcome to Ravenbase"
- **Input labels:** always ABOVE the input (never floating), `text-sm font-medium`
- **Error text:** `text-xs text-destructive` immediately below input
- **Primary button:** `rounded-full w-full` 
- **Skip link:** `Button variant="ghost"` — not visually prominent
- **Step indicator:** dots or line — use `bg-primary` for completed, `bg-secondary` for upcoming
- **Progress bar:** shadcn `<Progress>` component for SSE progress

---

## Known Bugs / Current State

**BUG-005 (HIGH):** OnboardingWizard.tsx calls `router.push("/dashboard")` on completion → 404.
- **Root cause:** `components/domain/OnboardingWizard.tsx:97` has `router.push("/dashboard")` and line 134 has `router.replace("/dashboard")`. The route `/dashboard` doesn't exist (only `app/(dashboard)/` group exists, which serves pages at `/chat`, `/inbox`, etc.).
- **Fix:** Search all occurrences of `/dashboard` in OnboardingWizard.tsx and replace with `/chat`. Look for: `router.push("/dashboard")`, `router.replace("/dashboard")`, `redirect("/dashboard")`, `href="/dashboard"`.
- **Verification:** Complete onboarding as new user → should land at `/chat` not 404.
- **Story:** STORY-039

**ROUTE DOC BUG:** Existing docs reference `app/(dashboard)/onboarding/page.tsx` — this is wrong. Correct location is `app/(auth)/onboarding/page.tsx`. All docs that say `/dashboard/onboarding` must be corrected.

---

## Acceptance Criteria

- [ ] New user completes registration → lands on `/onboarding` (not `/chat` directly)
- [ ] `/onboarding` renders WITHOUT sidebar, WITHOUT DashboardHeader
- [ ] Step 1: Enter profile name → blur validation after 300ms → shows error if < 2 chars
- [ ] Step 1: Click "Continue" → `POST /v1/profiles` fires → profile created in DB
- [ ] Step 2: Drop PDF/DOCX → upload fires → SSE progress visible → "completed" shows
- [ ] Step 2: Click "Skip for now →" → proceeds to completion without upload
- [ ] Completion: `router.push("/chat")` — lands at `/chat`, NOT `/dashboard` (not 404)
- [ ] Profile appears in sidebar profile selector after onboarding
- [ ] Admin user: "Quick Setup" button creates default profile → immediately at `/chat`
- [ ] Mobile (375px): wizard steps stack, upload area full-width

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `BE-COMP-05-AuthSystem.md` — Clerk webhook that creates user record + 500 credits
- `BE-COMP-01-IngestionPipeline.md` — optional first upload flow
- `docs/architecture/03-api-contract.md` — profiles and ingest endpoints
- `docs/components/REFACTOR_PLAN.md` — BUG-005 fix details (router.push("/dashboard") → "/chat")

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-019](../stories/EPIC-06-auth-profiles/STORY-019.md) | Onboarding Wizard | Frontend | Profile creation + first upload flow |

---

## Component Files

```
app/(auth)/onboarding/   ← CORRECT LOCATION (not dashboard!)
  page.tsx            — Orchestrates wizard steps
  loading.tsx         — Skeleton loading state

components/domain/
  OnboardingWizard.tsx     — Multi-step wizard container
  ProfileNameStep.tsx      — Step 1: profile name input
  FileUploadStep.tsx       — Step 2: optional file upload
  IngestionProgress.tsx    — SSE progress for uploaded file
  OnboardingComplete.tsx   — Completion state before redirect
```

## Step Pattern

```tsx
// OnboardingWizard.tsx — BUG-005 FIX: router.push("/chat") not "/dashboard"
type Step = "profile" | "upload" | "complete"

const handleFileUpload = async (file: File) => {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("profile_id", profile.id)
  const { source_id } = await apiUpload<{ source_id: string }>("/v1/ingest/upload", formData)
  setUploadedSourceId(source_id)
  setStep("complete")
}

// BUG-005 FIX — was router.push("/dashboard")
const handleComplete = () => router.push("/chat")
```

## Profile Name Input Pattern

```tsx
// ProfileNameStep.tsx — blur + 300ms debounce validation per RULE-18
const handleBlur = () => {
  setTouched(true)
  clearTimeout(timerRef.current)
  timerRef.current = setTimeout(() => {
    if (value.length > 0 && value.length < 2) {
      setError("Name must be at least 2 characters")
    } else {
      setError(null)
    }
  }, 300)
}
```

## File Upload with react-dropzone

```tsx
// FileUploadStep.tsx — full upload with SSE progress
const { getRootProps, getInputProps, isDragActive } = useDropzone({
  accept: {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"]
  },
  maxSize: 50 * 1024 * 1024,
  onDrop: async (acceptedFiles) => {
    const file = acceptedFiles[0]
    const formData = new FormData()
    formData.append("file", file)
    formData.append("profile_id", profileId)
    const { source_id } = await apiUpload<{ source_id: string }>("/v1/ingest/upload", formData)
    const token = await getToken()
    setStreamUrl(`/api/v1/ingest/stream/${source_id}?token=${token}`)
  }
})
```
