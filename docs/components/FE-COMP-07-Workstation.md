# Workstation

> **Component ID:** FE-COMP-07
> **Epic:** EPIC-05 — Meta-Document Generation
> **Stories:** STORY-017
> **Type:** Frontend (Dashboard)

---

## Purpose

The Workstation is the dedicated workspace for generating, viewing, and exporting Meta-Documents. It provides a split-panel layout (document history sidebar + editor), a real-time streaming Markdown editor that renders tokens as they arrive via SSE, and export functionality. It is the primary output surface for Ravenbase's generative AI capabilities. Accessible at `/workstation`.

---

## User Journey

1. User navigates to `/workstation`
2. Left panel: history of previous Meta-Docs for active profile
3. User types prompt in `PromptInput`:
   - Example: "Summarize my technical decisions from Q3 2024"
4. Clicks "Generate":
   a. `POST /v1/metadoc/generate {prompt, profile_id, model?}` → `{job_id, estimated_credits}`
   b. `◆ GENERATING...` status indicator appears (with `animate-pulse`)
   c. SSE stream opens: `GET /v1/metadoc/stream/{job_id}?token={clerk_jwt}`
   d. Tokens render in real-time to MetaDocEditor (`ReactMarkdown`)
5. Completion:
   a. SSE sends `{type: "done", doc_id, credits_consumed}`
   b. `◆ SAVED_JUST_NOW` indicator
   c. History panel updates
   d. Sidebar credit balance decrements (admin: no change)
6. Export options:
   a. Download `.md` → `Blob({content}, type: "text/markdown")`
   b. Print → `window.print()` with `@media print` CSS

**History panel:**
- Left sidebar lists all previous Meta-Docs for active profile
- Click item → `GET /v1/metadoc/{doc_id}` → loads content into editor
- **BUG-017:** Clicking sets `activeContent=""` — content never loaded (must fix)

**Admin bypass:**
- Meta-Doc generation costs 18 (Haiku) or 45 (Sonnet) credits
- Admin users: backend credit check skipped → tokens stream, doc saves, 0 credits deducted
- Frontend: same UI, sidebar shows `◆ ADMIN_ACCESS`

---

## Subcomponents

```
components/domain/
  Workstation.tsx        — Main layout (history panel + editor + prompt)
  MetaDocEditor.tsx      — SSE stream consumer + Markdown renderer (BUG-016: auto-save missing)
  MetaDocHistory.tsx     — Left panel, document list (BUG-017: content never loaded on click)
  SourcesPanel.tsx       — Slide-over showing contributing Memory nodes
  PromptInput.tsx        — Bottom prompt textarea + Generate button
  SaveStatus.tsx         — ◆ SAVED_JUST_NOW / ◆ UNSAVED_CHANGES indicator

hooks/
  use-sse.ts             — Reusable SSE hook (also used by IngestionProgress)
  use-autosave.ts        — Auto-save to localStorage every 30s (BUG-016 fix lives here)
  use-document-history.ts — TanStack Query wrapper for Meta-Doc list

app/(dashboard)/workstation/
  page.tsx               — Page composing Workstation component
  loading.tsx            — Skeleton loading state
```

---

## API Contracts

```
POST /v1/metadoc/generate
  Request:  { prompt: string, profile_id?: string, model?: "haiku" | "sonnet" }
  Response: { job_id: string, estimated_credits: number }
  Auth:     Required
  Cost:     18 credits (Haiku), 45 credits (Sonnet) — 0 for admin

GET /v1/metadoc/stream/{job_id}?token={clerk_jwt}
  Type:     SSE (text/event-stream)
  Events:
    { type: "token", content: string }
    { type: "done", doc_id: string, credits_consumed: number }
    { type: "error", message: string }
  Note:     token as query param — EventSource cannot set headers

GET /v1/metadoc
  Response: { documents: [{id, title, original_prompt, generated_at, credits_consumed}] }
  Auth:     Required
  staleTime: 30_000

GET /v1/metadoc/{doc_id}
  Response: { id, title, content_markdown, original_prompt, generated_at, credits_consumed }
  Auth:     Required
  Used by:  MetaDocHistory onClick (BUG-017 — must actually call this)
```

---

## Admin Bypass

Generation costs 18 (Haiku) or 45 (Sonnet) credits per call.
Admin users: backend `CreditService.check_or_raise()` returns early → LLM runs → no credit deduction.
Frontend: same UI — sidebar shows `◆ ADMIN_ACCESS` instead of credit balance.

---

## Auto-save State Machine (RULE-19)

The Workstation MUST implement the auto-save state machine per RULE-19. This is NOT optional.

States shown as mono label in editor header:
```
◆ SAVED_JUST_NOW     → immediately after SSE done event + localStorage save
◆ SAVED_2_MIN_AGO    → 2 min after last save (set by setTimeout)
◆ UNSAVED_CHANGES    → SSE disconnected before done (network error) OR localStorage write failed
◆ GENERATING...      → while SSE is active (animate-pulse)
```

Save to `localStorage` every 30 seconds while editing. Key: `ravenbase-draft-${profileId}`.

**BUG-016 prevents this from working** — see Known Bugs below.

---

## Design System Rules

Cross-reference: `docs/design/AGENT_DESIGN_PREAMBLE.md` (READ FIRST)
Cross-reference: `docs/design/04-ux-patterns.md` — streaming SSE patterns

Specific rules:
- **Layout:** `flex h-dvh` — use `h-dvh` not `h-screen` (RULE-12)
- **History sidebar:** `hidden md:flex w-64 flex-col border-r border-border bg-card`
- **Prompt input sticky:** `sticky bottom-0 p-4 pb-[max(1rem,env(safe-area-inset-bottom))]` (RULE-13)
- **Streaming content:** wrapped in `aria-live="polite" aria-atomic="false"` (RULE-17)
- **Save status label:** `font-mono text-xs text-muted-foreground` + `◆` prefix (RULE-19)
- **Generating status:** `animate-pulse` on the `◆ GENERATING...` label
- **History item active:** `bg-primary/10 border border-primary/20 rounded-lg`
- **History item hover:** `hover:bg-secondary rounded-lg`
- **Export buttons:** `rounded-full` — never `rounded-md`
- **Markdown area:** `prose prose-sm max-w-none` — shadcn typography plugin

---

## Known Bugs / Current State

**BUG-016 (HIGH — RULE-19 VIOLATION):** MetaDocEditor auto-save NOT implemented.
- **Root cause:** `components/domain/MetaDocEditor.tsx` shows the `◆ SAVED_JUST_NOW` / `◆ UNSAVED_CHANGES` status labels but never actually calls `localStorage.setItem()`. The `use-autosave.ts` hook exists but is not connected to the editor content. The labels update based on SSE status alone, not actual save operations.
- **Fix:** Wire `useAutosave(content, `ravenbase-draft-${profileId}`, 30_000)` in `MetaDocEditor.tsx`. The `use-autosave.ts` hook must call `localStorage.setItem(key, content)` on the 30s interval and update status accordingly.
- **Story:** STORY-039

**BUG-017 (HIGH):** MetaDocHistory clicking a previous doc sets `activeContent=""` — content never loaded.
- **Root cause:** `components/domain/MetaDocHistory.tsx` calls `onSelect(doc.id)` when a history item is clicked. In `Workstation.tsx`, the `onSelect` handler sets `setActiveDocId(docId)` but `MetaDocEditor`'s `useEffect([docId])` that fetches `GET /v1/metadoc/{docId}` is broken — it sets `content=""` before the fetch resolves and the fetch result never updates the state correctly.
- **Fix:** In `MetaDocEditor.tsx`, fix the `useEffect` that loads existing docs:
  ```typescript
  useEffect(() => {
    if (!docId) return
    setContent("")  // clear while loading — OK
    apiFetch<{ content_markdown: string }>(`/v1/metadoc/${docId}`)
      .then((d) => setContent(d.content_markdown))  // must use content_markdown field
      .catch(() => toast.error("Failed to load document"))
  }, [docId])
  ```
- **Story:** STORY-039

---

## Acceptance Criteria

- [ ] `/workstation` renders two-panel layout (history + editor) on desktop
- [ ] Type prompt + click Generate → `POST /v1/metadoc/generate` fires
- [ ] `◆ GENERATING...` (with `animate-pulse`) shows while SSE is active
- [ ] Tokens stream into editor in real-time via SSE
- [ ] Markdown renders: **bold**, `code`, headings, lists, blockquotes
- [ ] After SSE done: `◆ SAVED_JUST_NOW` shown + `localStorage.setItem` called (BUG-016 fixed)
- [ ] Click history item → `GET /v1/metadoc/{id}` fires → `content_markdown` loaded (BUG-017 fixed)
- [ ] Export `.md` → file downloads with correct content and filename
- [ ] Print → browser print dialog opens
- [ ] Mobile (375px): history hidden, `History` button opens bottom Sheet
- [ ] Prompt input sticky at bottom with safe-area padding
- [ ] Streaming content in `aria-live="polite"` region
- [ ] Admin user generates doc → credit balance unchanged

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `docs/design/04-ux-patterns.md` — streaming patterns, auto-save state machine
- `BE-COMP-04-GenerationEngine.md` — Meta-Doc generation pipeline, SSE streaming
- `BE-COMP-06-CreditSystem.md` — credit costs (18 Haiku / 45 Sonnet), admin bypass
- `docs/architecture/03-api-contract.md` — metadoc endpoints
- `docs/components/REFACTOR_PLAN.md` — BUG-016, BUG-017 fix details

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-017](docs/stories/EPIC-05-metadoc/STORY-017.md) | Workstation UI | Frontend | Full Workstation implementation |
| [STORY-016](docs/stories/EPIC-05-metadoc/STORY-016.md) | Meta-Doc Generation Pipeline | Backend | SSE streaming + generation API |

---

## useSSE Hook (Reusable)

```tsx
// hooks/use-sse.ts
"use client"
import { useEffect, useState } from "react"

type SSEStatus = "idle" | "streaming" | "done" | "error"

export function useSSE(url: string | null) {
  const [data, setData] = useState("")
  const [status, setStatus] = useState<SSEStatus>("idle")

  useEffect(() => {
    if (!url) return
    setData("")
    setStatus("streaming")

    const es = new EventSource(url)

    es.onmessage = (e) => {
      const parsed = JSON.parse(e.data)
      if (parsed.type === "token") setData((prev) => prev + parsed.content)
      if (parsed.type === "done") { setStatus("done"); es.close() }
      if (parsed.type === "error") { setStatus("error"); es.close() }
    }

    es.onerror = () => { setStatus("error"); es.close() }

    return () => es.close()  // cleanup on unmount — prevents memory leak
  }, [url])

  return { data, status }
}
```

## Auto-save Hook (BUG-016 fix)

```tsx
// hooks/use-autosave.ts — connect this to MetaDocEditor content
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
          localStorage.setItem(key, content)  // BUG-016 fix: actually save
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

## MetaDocHistory onClick Fix (BUG-017)

```tsx
// In MetaDocEditor.tsx — FIXED useEffect that loads existing docs
useEffect(() => {
  if (!docId) { setContent(""); return }
  apiFetch<{ content_markdown: string }>(`/v1/metadoc/${docId}`)
    .then((d) => setContent(d.content_markdown))  // BUG-017 fix: was setting ""
    .catch(() => toast.error("Failed to load document"))
}, [docId, apiFetch])
```

## Mobile Layout

```tsx
// app/(dashboard)/workstation/page.tsx
<div className="flex h-dvh">
  {/* Desktop: history sidebar */}
  <aside className="hidden md:flex w-64 flex-col border-r border-border">
    <MetaDocHistory profileId={profileId} activeDocId={activeDocId} onSelect={setActiveDocId} />
  </aside>

  {/* Editor area */}
  <main className="flex-1 flex flex-col min-w-0">
    <MetaDocEditor docId={activeDocId} profileId={profileId} />
    {/* Sticky prompt with safe-area padding (RULE-13) */}
    <div className="sticky bottom-0 border-t bg-background
                    pb-[max(1rem,env(safe-area-inset-bottom))] p-4">
      <PromptInput onSubmit={handleGenerate} disabled={isGenerating} />
    </div>
  </main>

  {/* Mobile: History Sheet */}
  <Sheet open={showHistory} onOpenChange={setShowHistory}>
    <SheetContent side="bottom" className="h-[80vh]">
      <SheetTitle>Document History</SheetTitle>
      <MetaDocHistory profileId={profileId} activeDocId={activeDocId}
        onSelect={(id) => { setActiveDocId(id); setShowHistory(false) }} />
    </SheetContent>
  </Sheet>
</div>
```
