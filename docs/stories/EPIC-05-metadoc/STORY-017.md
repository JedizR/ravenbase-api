# STORY-017: Workstation UI (Streaming + Markdown + Export)

**Epic:** EPIC-05 — Meta-Document Generation
**Priority:** P0
**Complexity:** Medium
**Depends on:** STORY-016

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
- FR-08-AC-4: Output streamed via SSE (token by token)

## Component
COMP-04: GenerationEngine

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (apiFetch, no form tags, Tailwind only)
> 3. `docs/design/03-screen-flows.md` — Workstation layout spec (prompt input, editor area, history panel)
> 4. `docs/design/02-component-library.md` — shadcn components used in Workstation
> 5. `docs/architecture/03-api-contract.md` — `POST /v1/metadoc/generate` + `GET /v1/metadoc/stream/{job_id}` spec

---

## User Story
As a user, I want a dedicated workspace where I can generate, view, and export my Meta-Documents.

## Acceptance Criteria
- [ ] AC-1: Workstation accessible at `/workstation`
- [ ] AC-2: Prompt input at bottom; on submit, opens SSE stream and streams Markdown to editor
- [ ] AC-3: Streaming text renders as formatted Markdown in real-time (not raw text)
- [ ] AC-4: "Export as Markdown" button downloads `.md` file
- [ ] AC-5: "Export as PDF" button triggers browser print dialog with print-optimized CSS
- [ ] AC-6: Document history panel (left sidebar): lists previous Meta-Docs, click to load
- [ ] AC-7: "Sources" button shows which Memory nodes contributed (links to Graph Explorer nodes)
- [ ] AC-8: Mobile (< 768px): history sidebar hidden by default; accessible via a
  "History" button that opens a bottom Sheet (shadcn Sheet component)
- [ ] AC-9: Mobile (< 768px): prompt input is sticky to bottom of screen with
  safe-area padding for iOS home indicator

## Technical Notes

### Files to Create (Frontend)
- `components/domain/Workstation.tsx` — main layout with history panel + editor
- `components/domain/MetaDocEditor.tsx` — SSE stream consumer + Markdown renderer
- `components/domain/MetaDocHistory.tsx` — left panel, document list
- `hooks/use-sse.ts` — reusable SSE hook (also used in IngestionProgress from STORY-007)
- `app/(dashboard)/workstation/page.tsx`

### Additional Package Required
```bash
npm install react-markdown remark-gfm
```

### Mobile Layout

The two-panel layout (history sidebar + editor) collapses on mobile:

```tsx
{/* Desktop: split panel. Mobile: full-width with sheet for history */}
<div className="flex h-full">
  {/* History sidebar — hidden on mobile */}
  <aside className="hidden md:flex w-64 flex-col border-r border-border">
    <MetaDocHistory />
  </aside>
  {/* Editor — full width on mobile */}
  <main className="flex-1 flex flex-col">
    <MetaDocEditor />
    {/* Prompt — sticky bottom on mobile */}
    <div className="sticky bottom-0 p-4 border-t bg-background
                    pb-[max(1rem,env(safe-area-inset-bottom))]">
      <PromptInput />
    </div>
  </main>
</div>
```

### Architecture Constraints
- No `<form>` tags — prompt input uses controlled div + onClick
- All API calls via `apiFetch` — never raw `fetch()`
- `use-sse.ts` hook is reusable — not workstation-specific
- Export as Markdown: create Blob and trigger anchor download (no server round-trip)
- Export as PDF: `window.print()` with `@media print` CSS hiding UI chrome

### Reusable SSE Hook
```typescript
// hooks/use-sse.ts
"use client";
import { useEffect, useState } from "react";

export function useSSE(url: string | null) {
  const [data, setData] = useState<string>("");
  const [status, setStatus] = useState<"idle" | "streaming" | "done" | "error">("idle");

  useEffect(() => {
    if (!url) return;
    setData("");
    setStatus("streaming");

    const es = new EventSource(url);
    es.onmessage = (e) => {
      const parsed = JSON.parse(e.data);
      if (parsed.type === "token") setData((prev) => prev + parsed.content);
      if (parsed.type === "done") { setStatus("done"); es.close(); }
      if (parsed.type === "error") { setStatus("error"); es.close(); }
    };
    es.onerror = () => { setStatus("error"); es.close(); };

    return () => es.close();
  }, [url]);

  return { data, status };
}
```

### Export as Markdown Pattern
```typescript
const handleExportMarkdown = () => {
  const blob = new Blob([docContent], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `meta-doc-${Date.now()}.md`;
  a.click();
  URL.revokeObjectURL(url);
};
```

### Prompt Submit Pattern (no form tag)
```typescript
// In MetaDocEditor.tsx
const [streamUrl, setStreamUrl] = useState<string | null>(null);
const { data, status } = useSSE(streamUrl);

const handleGenerate = async () => {
  const { job_id } = await apiFetch<{ job_id: string }>("/v1/metadoc/generate", {
    method: "POST",
    body: JSON.stringify({ prompt, profile_id: activeProfile?.id, model: "sonnet" }),
  });
  const token = await getToken(); // Clerk token
  setStreamUrl(`/api/v1/metadoc/stream/${job_id}?token=${token}`);
};
```

## Definition of Done
- [ ] Markdown renders in real-time as tokens stream in
- [ ] "Export as Markdown" produces valid .md file download
- [ ] "Export as PDF" triggers browser print dialog
- [ ] Document history panel lists and loads previous docs
- [ ] Mobile: prompt input is fixed to bottom (tested at 375px)
- [ ] `npm run build` passes (0 TypeScript errors)

## Final Localhost Verification (mandatory before marking complete)

After `npm run build` passes and all tests pass, verify the running application works:

**Step 1 — Clear stale cache:**
```bash
rm -rf .next
```

**Step 2 — Start dev server:**
```bash
npm run dev
```

**Step 3 — Verify no runtime errors:**
- Open http://localhost:3000 in the browser
- Sign in if redirected to /login
- Navigate to `/workstation`
- Confirm NO "Internal Server Error" or webpack runtime errors
- Confirm CSS loads correctly (no unstyled content)
- Open browser DevTools → Console tab
- Confirm no red errors (yellow warnings acceptable)

**Step 4 — Report one of:**
- ✅ `localhost verified` — page renders correctly
- ⚠️ `Issue found: [describe issue]` — fix before committing docs

Only commit the docs update (epics.md, story-counter, project-status, journal) AFTER localhost verification passes.

## Testing This Story

```bash
# Frontend build:
npm run build

# Manual test:
# 1. Open http://localhost:3000/workstation
# 2. Type a prompt: "Summarize my skills in Python and machine learning"
# 3. Click Generate — verify Markdown streams in real-time
# 4. Click "Export as Markdown" — verify .md file downloads
# 5. Click "Export as PDF" — verify browser print dialog opens
# 6. Check history panel — verify previous doc appears
# 7. Click history item — verify doc loads in editor
# 8. Resize to 375px — verify prompt input is fixed to bottom
```

**Passing result:** Markdown streams in real-time. Export to .md and PDF both work. History panel loads previous documents. Mobile layout correct.

---

## Agent Implementation Brief

```
Implement STORY-017: Workstation UI (Streaming + Markdown + Export).

Read first:
1. CLAUDE.md (architecture rules)
2. docs/design/AGENT_DESIGN_PREAMBLE.md — NON-NEGOTIABLE visual rules, anti-patterns, and pre-commit checklist. Read fully before writing any JSX.
3. docs/design/00-brand-identity.md — logo spec, voice rules, mono label pattern
4. docs/design/01-design-system.md — all color tokens, typography
5. docs/design/CLAUDE_FRONTEND.md (no form tags, apiFetch, Tailwind only)
6. docs/design/03-screen-flows.md (Workstation layout — history panel + editor + prompt input)
7. docs/architecture/03-api-contract.md (POST /v1/metadoc/generate + stream spec)
8. docs/stories/EPIC-05-metadoc/STORY-017.md (this file)

Key constraints:
- Install: npm install react-markdown remark-gfm
- No <form> tags — prompt area is a div + Textarea + onClick button
- hooks/use-sse.ts is a REUSABLE hook — not embedded in a component
- EventSource URL: /api/v1/metadoc/stream/{job_id}?token={clerk_token}
- Export as Markdown: Blob + anchor click (no server call)
- Export as PDF: window.print() + @media print CSS

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
git add -A && git commit -m "feat(ravenbase): STORY-017 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-017"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-017
git add docs/stories/epics.md && git commit -m "docs: mark STORY-017 complete"
```
