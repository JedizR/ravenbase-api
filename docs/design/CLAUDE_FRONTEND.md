# Ravenbase Frontend — Agent Instructions (CLAUDE_FRONTEND.md)

> Copy this file to `ravenbase-web/CLAUDE_FRONTEND.md`

---

## Frontend Architecture Rules (Never Violate)

```
RULE 1: No <form> tags. EVER.
  Use onClick handlers and controlled inputs.
  ❌ <form onSubmit={...}> → <button type="submit">
  ✅ <div> → <button onClick={handleSubmit}>

RULE 2: All styling via Tailwind classes only.
  No inline styles. No CSS modules. No styled-components.
  ❌ style={{ color: '#1e3a5f' }}
  ✅ className="text-primary"

RULE 3: All API calls via apiFetch() from lib/api.ts.
  Never call fetch() directly. Never hardcode API URLs.
  ❌ fetch(`http://localhost:8000/v1/search`, ...)
  ✅ apiFetch<SearchResponse>("/v1/search", {...})

RULE 4: All API response data validated with Zod.
  The generated API client provides types, but always validate at runtime.
  Use the schema from lib/api-client/ as the source of truth.

RULE 5: Route groups do NOT force color mode.
  (marketing)/ → light by default, no auth required
  (auth)/      → light by default, no auth required
  (dashboard)/ → light by default, auth required (middleware.ts)
  Dark mode is global — toggled via .dark on <html>, stored in localStorage.
  Never add className="dark" or className="light" to route group layouts.

RULE 6: TanStack Query for all server state.
  Never useState + useEffect for API data.
  Use useQuery for reads, useMutation for writes.

RULE 7: shadcn/ui for all base components.
  Check components/ui/ before building a new component.
  Import: import { Button } from "@/components/ui/button"
  Never re-implement what shadcn provides.

RULE 8: TypeScript strict mode. Zero 'any'.
  tsconfig.json has "strict": true.
  Use 'unknown' and type narrowing instead of 'any'.

RULE 9: Use the brand logo components — never the old placeholder.
  ❌ <div className="w-6 h-6 border-2 rounded-sm"><span>R</span></div>
  ❌ <Brain className="w-3 h-3" /> as a logo substitute
  ✅ import { RavenbaseLogo, RavenbaseLockup } from "@/components/brand"
  The component files are created in STORY-001-WEB as part of web scaffolding.

RULE 10: Every dashboard page must have a loading.tsx sibling.
  ❌ No loading state — page shows blank while data fetches
  ✅ app/(dashboard)/inbox/loading.tsx with skeleton matching page structure

RULE 11: Touch targets must be at least 44px tall on mobile.
  ❌ <Button size="sm"> inside a mobile-primary interface (h-8 = 32px)
  ✅ <Button size="sm" className="h-11 sm:h-8">

RULE 12: Use h-[100dvh] instead of h-screen for full-height mobile layouts.
  ❌ className="h-screen"  — causes iOS Safari address-bar layout shift
  ✅ className="h-[100dvh]"

RULE 13: Sticky bottom elements need safe-area-inset padding.
  ❌ className="sticky bottom-0 p-4"
  ✅ className="sticky bottom-0 p-4 pb-[max(1rem,env(safe-area-inset-bottom))]"

RULE 14: Use next/font for all typefaces — never @import from Google Fonts directly.
  Why: @import causes a render-blocking network request. next/font preloads fonts
  during build, eliminates layout shift (CLS), and self-hosts them on Vercel CDN.
  ❌ In globals.css: @import url('https://fonts.googleapis.com/css2?family=DM+Sans...')
  ✅ In app/layout.tsx:
     import { DM_Sans, Playfair_Display, JetBrains_Mono } from "next/font/google"
     const dmSans = DM_Sans({ subsets: ["latin"], display: "swap", variable: "--font-sans" })
     const playfair = Playfair_Display({ subsets: ["latin"], display: "swap", variable: "--font-serif" })
     const jetbrains = JetBrains_Mono({ subsets: ["latin"], display: "swap", variable: "--font-mono" })
     // Apply: <html className={`${dmSans.variable} ${playfair.variable} ${jetbrains.variable}`}>

RULE 15: Every marketing page must export a metadata object. Dashboard pages must be noindexed.
  Why: Without metadata, Google shows "Untitled" in search results. Without noindex on
  dashboard routes, authenticated pages get crawled and confuse search engines.
  ✅ Marketing pages (app/(marketing)/page.tsx):
     export const metadata: Metadata = {
       title: "Ravenbase — Your knowledge, permanent and queryable",
       description: "...",
       openGraph: { ... },
       twitter: { ... },
     }
  ✅ Dashboard layout (app/(dashboard)/layout.tsx):
     export const metadata: Metadata = { robots: { index: false, follow: false } }
  ✅ Root layout (app/layout.tsx):
     export const metadata: Metadata = {
       metadataBase: new URL("https://ravenbase.app"),
       // metadataBase MUST be set — without it OG images become relative URLs
       // that social platforms cannot fetch
     }

RULE 16: Every page must have a skip link as its first focusable element.
  ✅ <a href="#main-content" className="sr-only focus:not-sr-only ...">Skip to main content</a>
  ✅ <main id="main-content"> wraps all page content
  This is required for WCAG 2.1 AA 2.4.1 compliance.

RULE 17: All streaming SSE content must be wrapped in aria-live="polite" regions.
  ✅ Chat and Workstation streaming output: <div aria-live="polite" aria-atomic="false">
  ✅ Status messages (progress, confirmations): <div role="status" aria-live="polite" className="sr-only">
  This announces AI-generated content to screen reader users.

RULE 18: Form fields validate on blur with a 300ms debounce — never on every keystroke, never only on submit.
  Why: Keystroke validation triggers errors while the user is mid-word, creating false anxiety.
  Submit-only validation makes users hunt for errors after the fact. Blur + debounce is the
  correct UX — it validates after the user leaves a field, giving them space to finish typing.

  Label placement:
  ❌ Floating labels / inline placeholder-as-label (disappears when typing, removes context)
  ✅ Labels always ABOVE the input with consistent font-medium text-sm

  Error placement:
  ❌ Errors aggregated at top of form
  ✅ Error text immediately BELOW the relevant input, text-destructive text-xs

  Validation timing:
  ❌ onChange: triggers on every keystroke
  ❌ onSubmit only: user submits, then hunts for errors
  ✅ onBlur with 300ms debounce using useRef timeout

  Implementation pattern (use this for every form field in the codebase):
  ```tsx
  // Correct blur-debounce validation pattern
  import { useState, useRef } from "react"

  function ValidatedInput({ name, label, validate, ...props }) {
    const [error, setError] = useState<string | null>(null)
    const [touched, setTouched] = useState(false)
    const timerRef = useRef<ReturnType<typeof setTimeout>>()

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      setTouched(true)
      clearTimeout(timerRef.current)
      // 300ms debounce: validate after user has finished leaving the field
      timerRef.current = setTimeout(() => {
        const result = validate(e.target.value)
        setError(result ?? null)
      }, 300)
    }

    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={name} className="text-sm font-medium text-foreground">
          {label}
        </label>
        <input
          id={name}
          name={name}
          onBlur={handleBlur}
          aria-invalid={touched && !!error}
          aria-describedby={error ? `${name}-error` : undefined}
          className={touched && error ? "border-destructive" : ""}
          {...props}
        />
        {touched && error && (
          <p id={`${name}-error`} className="text-xs text-destructive" role="alert">
            {error}
          </p>
        )}
      </div>
    )
  }
  ```

  Success state (show after successful blur-validation):
  ✅ Append a checkmark icon (CheckCircle2 from lucide-react) to the input's right side
  ❌ Do not change the border to green — it's distracting on dense forms

  React Hook Form note: if using react-hook-form, set mode: "onBlur" in useForm().
  Never set mode: "onChange" in production forms.
```

RULE 19: Show "Last saved" status indicator in the Workstation editor (auto-save context).
  This is the highest-trust signal in productivity SaaS — users need to know their work is safe.
  Save to localStorage every 30 seconds while editing. Display using the ◆ mono label pattern.
  ✅ <span className="font-mono text-xs text-muted-foreground">◆ SAVED_JUST_NOW</span>
  States: "◆ SAVED_JUST_NOW" → "◆ SAVED_2_MIN_AGO" → "◆ UNSAVED_CHANGES" (on write failure)
  Visible in Workstation header, next to Export buttons.

---

## Design System Quick Reference

**Default mode:** Light. Dark mode via `.dark` on `<html>`. No route group forces color mode.

**Fonts:**
- `font-sans` — DM Sans (body, UI elements)
- `font-serif` — Playfair Display (headlines, section titles)
- `font-mono` — JetBrains Mono (labels, code, system text)

**Key colors (light mode):**
- `bg-background` → `#f5f3ee` (warm cream — page background)
- `bg-card` → `#ffffff` (elevated surfaces)
- `bg-primary` → `#2d4a3e` (forest green — CTAs, sidebar, active states)
- `bg-secondary` → `#e8ebe6` (subtle hover, muted surfaces)
- `bg-accent` → `#a8c4b2` (sage green highlights)
- `bg-warning` → `#ffc00d` (amber — pending conflicts, low credits)
- `bg-success` → `#3d8b5a` (green — resolved states)
- `bg-destructive` → `#b53233` (red — errors, delete)
- `bg-info` → `#3f87c2` (blue — processing, informational)

**Component patterns:**
- Cards: `bg-card border border-border rounded-2xl p-6`
- Primary CTA: `bg-primary text-primary-foreground px-6 py-3 rounded-full`
- Sidebar: `bg-primary text-primary-foreground` (green sidebar, always)
- Mono labels: `text-xs font-mono text-muted-foreground tracking-wider`
- Active conflict: `border-2 border-primary` on card
- Inactive conflict: `border-border opacity-70`
- Toasts: Use `sonner` — `import { toast } from "sonner"`

**Warning color rule:**
`bg-warning` elements MUST use `text-[var(--warning-foreground)]` or `text-foreground` for readable text.
Never use `text-white` on `bg-warning`.

**Tailwind version:** v4 (no tailwind.config.js — config lives in globals.css)

## API Client Usage — Server vs Client Components

> **Rule:** If the file has `"use client"` at the top → use `useApiFetch()` hook.
> If not (Server Component) → use `apiFetch()` directly.

### Pattern A: Server Components (no "use client" — pages, layouts, Server Actions)

```typescript
// lib/api.ts
import { auth } from "@clerk/nextjs/server";

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const { getToken } = auth();
  const token = await getToken();
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}${path}`,
    {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...init?.headers,
      },
    },
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message ?? "API error");
  }
  return response.json() as Promise<T>;
}
```

### Pattern B: Client Components ("use client" — all dashboard domain components)

```typescript
// lib/api-client.ts
import { useAuth } from "@clerk/nextjs";

export function useApiFetch() {
  const { getToken } = useAuth();

  return async function apiFetch<T>(
    path: string,
    init?: RequestInit,
  ): Promise<T> {
    const token = await getToken();
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}${path}`,
      {
        ...init,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...init?.headers,
        },
      },
    );
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail?.message ?? "API error");
    }
    return response.json() as Promise<T>;
  };
}
```

Usage with TanStack Query (most common pattern in dashboard):
```typescript
"use client";
import { useApiFetch } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";

export function ConflictList() {
  const apiFetch = useApiFetch();

  const { data, isLoading } = useQuery({
    queryKey: ["conflicts", "pending"],
    queryFn: () =>
      apiFetch<ConflictListResponse>("/v1/conflicts?status=pending"),
  });
}
```

### FormData uploads (no Content-Type header — browser sets multipart boundary):
```typescript
export function useApiUpload() {
  const { getToken } = useAuth();

  return async function apiUpload<T>(
    path: string,
    formData: FormData,
  ): Promise<T> {
    const token = await getToken();
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}${path}`,
      {
        method: "POST",
        body: formData,
        // Do NOT set Content-Type — browser must set multipart boundary
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail?.message ?? "Upload error");
    }
    return response.json() as Promise<T>;
  };
}
```

## Job Polling Pattern

```typescript
// For async jobs: useQuery with refetchInterval
const jobQuery = useQuery({
  queryKey: ["job", jobId],
  queryFn: () => apiFetch<JobStatus>(`/v1/ingest/status/${jobId}`),
  enabled: !!jobId,
  refetchInterval: (query) => {
    const s = query.state.data?.status;
    return s === "completed" || s === "failed" ? false : 2000;
  },
});
```

---

## Approved npm Packages

All others require explicit approval before `npm install`. Ask: package name + why + dev or prod.

### Pre-installed from scaffold (STORY-001 web setup)
All shadcn/ui dependencies from the components.json template.
`tw-animate-css` — dev dependency, required by globals.css (`@import "tw-animate-css"`)

### Additional approved packages

| Package | Install | Used in | Purpose |
|---|---|---|---|
| `framer-motion@^11` | prod | STORY-021 | Landing page scroll animations |
| `@tanstack/react-query@^5` | prod | All dashboard | Server state + polling |
| `cytoscape@^3.30` | prod | STORY-011 | Graph Explorer rendering |
| `cytoscape-fcose@^2.2` | prod | STORY-011 | Force-directed layout |
| `react-dropzone@^14` | prod | STORY-005-web | Drag-and-drop file upload |
| `react-markdown@^9` | prod | STORY-017 | Markdown rendering in Workstation |
| `remark-gfm@^4` | prod | STORY-017 | GitHub Flavoured Markdown |
| `@hey-api/openapi-ts@^0.53` | dev | After every backend story | TypeScript client generation |
| `msw@^2` | dev | Frontend stories before backend | Mock Service Worker for stubs |
| `vitest@^2` | dev | All | Unit tests |
| `@playwright/test@^1` | dev | E2E | Browser tests |

### Install command (run once during STORY-001 web scaffold):
```bash
npm install framer-motion @tanstack/react-query cytoscape cytoscape-fcose react-dropzone react-markdown remark-gfm
npm install -D @hey-api/openapi-ts msw vitest @playwright/test tw-animate-css
```

### generate-client command (run after every backend story that adds/changes endpoints):
```bash
# Backend API server must be running at localhost:8000
npm run generate-client
git add src/lib/api-client/
git commit -m "chore: regenerate API client after STORY-XXX"
```

---

## Frontend Performance Requirements

Every frontend story must implement these patterns. They are not optional.

### 1. Heavy components use dynamic import

Cytoscape.js (Graph Explorer) and heavy chart libraries must never be in the initial
bundle. Always dynamic-import them:

```tsx
// ✅ Correct — Cytoscape loads only when Graph Explorer mounts
import dynamic from "next/dynamic"

const GraphExplorer = dynamic(
  () => import("@/components/domain/GraphExplorer"),
  {
    ssr: false,
    loading: () => <Skeleton className="w-full h-[600px] rounded-2xl" />,
  }
)
```

Libraries that MUST use dynamic import:
- `cytoscape` + `cytoscape-fcose` (STORY-011)
- `react-markdown` + `remark-gfm` (STORY-017)

### 2. Loading states are mandatory on every async route

Every dashboard page must have a `loading.tsx` sibling that renders a skeleton layout
matching the page structure. No blank screens, no spinner-only loading states.

```
app/(dashboard)/
  inbox/
    page.tsx      ← the real page
    loading.tsx   ← skeleton that renders instantly during navigation
  graph/
    page.tsx
    loading.tsx
  workstation/
    page.tsx
    loading.tsx
```

Skeleton pattern:
```tsx
// app/(dashboard)/inbox/loading.tsx
import { Skeleton } from "@/components/ui/skeleton"

export default function InboxLoading() {
  return (
    <div className="p-6 space-y-4">
      <Skeleton className="h-8 w-48" />
      {[...Array(3)].map((_, i) => (
        <Skeleton key={i} className="h-32 w-full rounded-2xl" />
      ))}
    </div>
  )
}
```

### 3. TanStack Query stale times

Never use default stale times. Set appropriate stale times per query:

```tsx
// Conflict list — stale after 30s (conflicts don't change every second)
useQuery({ queryKey: ["conflicts"], queryFn: ..., staleTime: 30_000 })

// Graph nodes — stale after 60s (expensive to refetch)
useQuery({ queryKey: ["graph", "nodes"], queryFn: ..., staleTime: 60_000 })

// Credits balance — stale after 15s (changes after operations)
useQuery({ queryKey: ["credits"], queryFn: ..., staleTime: 15_000 })

// Chat sessions list — stale after 10s (user may create new ones)
useQuery({ queryKey: ["chat", "sessions"], queryFn: ..., staleTime: 10_000 })
```

### 4. Qdrant and Neo4j are fast — don't over-debounce search

The search endpoint is designed for < 200ms. Do NOT debounce search queries longer
than 300ms. At 300ms debounce the UI feels sluggish. Use 200ms.

---

## SEO Specification (Next.js 15 App Router)

### Rendering strategy by page type

| Page type | Rendering | SEO | Rationale |
|---|---|---|---|
| Landing page (`/`) | SSG | index, follow | Static marketing content — crawled and ranked |
| Pricing page (`/pricing`) | SSG | index, follow | Public product information |
| Privacy Policy (`/privacy`) | SSG | index, follow | Required for legal compliance |
| Terms of Service (`/terms`) | SSG | index, follow | Required for legal compliance |
| Auth pages (`/sign-in`, `/sign-up`) | SSG | noindex | No crawl value |
| Dashboard (`/dashboard/*`) | SSR/ISR | noindex, nofollow | Auth-gated, no crawl value |

### Root layout metadata (set once in `app/layout.tsx`)

```tsx
// app/layout.tsx
import { DM_Sans, Playfair_Display, JetBrains_Mono } from "next/font/google"

const dmSans = DM_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
})
const playfair = Playfair_Display({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif",
})
const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
})

export const metadata: Metadata = {
  metadataBase: new URL("https://ravenbase.app"),
  // metadataBase is REQUIRED — makes all relative OG image URLs absolute
  title: {
    default: "Ravenbase — What happened, where, and when. Always.",
    template: "%s | Ravenbase",
    // template: child pages render as "Pricing | Ravenbase"
  },
  description:
    "Ravenbase permanently captures, structures, and synthesizes your knowledge. " +
    "AI memory that never forgets, never overwrites, always cites its sources.",
  keywords: ["AI memory", "knowledge graph", "personal knowledge management",
             "exocortex", "PKM", "AI assistant memory"],
  authors: [{ name: "Ravenbase" }],
  creator: "Ravenbase",
  robots: { index: true, follow: true },  // default; overridden per route
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://ravenbase.app",
    siteName: "Ravenbase",
    title: "Ravenbase — What happened, where, and when. Always.",
    description:
      "Your knowledge, permanently captured and instantly queryable. " +
      "Build the memory layer your AI agents have been missing.",
    images: [{ url: "/og-image.png", width: 1200, height: 630,
               alt: "Ravenbase — AI Memory System" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Ravenbase — What happened, where, and when. Always.",
    description:
      "Your knowledge, permanently captured and instantly queryable.",
    images: ["/og-image.png"],
    creator: "@ravenbase",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${dmSans.variable} ${playfair.variable} ${jetbrains.variable}`}
    >
      <body>{children}</body>
    </html>
  )
}
```

### Dashboard layout — noindex all authenticated routes

```tsx
// app/(dashboard)/layout.tsx
import type { Metadata } from "next"

export const metadata: Metadata = {
  robots: { index: false, follow: false },
  // All dashboard routes are auth-gated — no crawl value
}
```

### Sitemap (`app/sitemap.ts` — auto-served at /sitemap.xml)

```tsx
// app/sitemap.ts
import { MetadataRoute } from "next"

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://ravenbase.app"
  return [
    { url: base,               lastModified: new Date(), changeFrequency: "monthly",  priority: 1.0 },
    { url: `${base}/pricing`,  lastModified: new Date(), changeFrequency: "monthly",  priority: 0.9 },
    { url: `${base}/privacy`,  lastModified: new Date(), changeFrequency: "yearly",   priority: 0.3 },
    { url: `${base}/terms`,    lastModified: new Date(), changeFrequency: "yearly",   priority: 0.3 },
    // Dashboard routes intentionally excluded — auth-gated
  ]
}
```

### Robots (`app/robots.ts` — auto-served at /robots.txt)

```tsx
// app/robots.ts
import { MetadataRoute } from "next"

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/dashboard/", "/api/", "/sign-in", "/sign-up"],
      },
    ],
    sitemap: "https://ravenbase.app/sitemap.xml",
  }
}
```

### JSON-LD Structured Data (SoftwareApplication schema for landing page)

```tsx
// app/(marketing)/page.tsx — add inside the page component
// Google uses SoftwareApplication schema to show rich results for apps
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Ravenbase",
  "applicationCategory": "ProductivityApplication",
  "operatingSystem": "Web",
  "description":
    "Ravenbase permanently captures, structures, and synthesizes your knowledge " +
    "across years of scattered data using a hybrid vector + knowledge graph architecture.",
  "url": "https://ravenbase.app",
  "offers": [
    { "@type": "Offer", "price": "0", "priceCurrency": "USD", "name": "Starter" },
    { "@type": "Offer", "price": "12", "priceCurrency": "USD", "name": "Pro",
      "priceSpecification": { "@type": "UnitPriceSpecification", "billingDuration": "P1M" } },
  ],
}

// In the JSX return — use Next.js Script for JSON-LD:
import Script from "next/script"
<Script
  id="structured-data"
  type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
/>
// Note: dangerouslySetInnerHTML is correct here — JSON-LD is NOT rendered HTML,
// it is structured data for crawlers. This is the Google-recommended pattern.
```

### Semantic HTML landmark rules (enforced on all pages)

```tsx
// Every page must use semantic landmark elements — not just <div>
// Semantic HTML signals page structure to search engines and screen readers.

// ✅ Landing page structure:
<html lang="en">
  <body>
    <header>           {/* Site header — nav, logo, CTA */}
      <nav>            {/* Primary navigation */}
        <a href="/">Home</a>
        <a href="/pricing">Pricing</a>
      </nav>
    </header>
    <main>             {/* Primary page content — ONE <main> per page */}
      <section aria-labelledby="hero-heading">
        <h1 id="hero-heading">What happened, where, and when. Always.</h1>
      </section>
      <section aria-labelledby="features-heading">
        <h2 id="features-heading">Core Features</h2>
        {features.map(f => <article key={f.id}>...</article>)}
      </section>
    </main>
    <footer>           {/* Footer — legal links, company info */}
      <nav aria-label="Footer navigation">
        <a href="/privacy">Privacy Policy</a>
        <a href="/terms">Terms of Service</a>
      </nav>
    </footer>
  </body>
</html>

// ✅ Dashboard page structure:
<html lang="en" className="dark"> {/* dark class set by useTheme() */}
  <body>
    <div className="flex h-[100dvh]">
      <nav aria-label="Dashboard navigation">  {/* Sidebar */}
        {/* Nav items */}
      </nav>
      <main>                                   {/* Main content area */}
        <header>                               {/* Page header with title */}
          <h1>Graph Explorer</h1>
        </header>
        {/* Page content */}
      </main>
    </div>
  </body>
</html>

// ❌ Never structure pages as <div> soup:
// <div className="wrapper"><div className="nav"><div className="content">...
```

### Preconnect resource hints (marketing layout only)

Add `<link rel="preconnect">` hints in `app/(marketing)/layout.tsx` for services
the user will connect to immediately after visiting the marketing site.

```tsx
// app/(marketing)/layout.tsx
// These hints tell the browser to pre-establish TCP+TLS connections
// before the user clicks any button — reduces perceived latency on CTAs.
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <head>
        {/* Clerk auth server — pre-warm connection for "Get Started" clicks */}
        <link rel="preconnect" href="https://clerk.accounts.dev" />
        {/* API server — pre-warm for any dashboard redirect after sign-in */}
        <link rel="dns-prefetch" href="https://api.ravenbase.app" />
      </head>
      {children}
    </>
  )
}
```

> **Note:** Use `preconnect` (full TCP+TLS handshake) only for Clerk — the auth
> server is always hit immediately on signup. Use `dns-prefetch` (DNS only) for
> the API server since it's only needed after successful auth.
>
> **Do NOT add preconnect for fonts** — `next/font` self-hosts all fonts on Vercel's
> CDN, so there is no external font server to pre-warm.

### `next/image` for all images (required for LCP and CLS)

```tsx
// NEVER use <img> tags. ALWAYS use next/image.
// next/image prevents layout shift (CLS), lazy-loads automatically,
// and serves WebP with optimal sizing.
import Image from "next/image"

// Above-the-fold hero image (use priority to preload):
<Image
  src="/hero-screenshot.png"
  alt="Ravenbase dashboard showing the knowledge graph with memory nodes"
  width={1200}
  height={800}
  priority  // ← REQUIRED for above-fold images (improves LCP score)
  className="rounded-2xl"
/>

// Below-the-fold images (omit priority — lazy loaded by default):
<Image
  src="/feature-inbox.png"
  alt="Memory Inbox showing conflict resolution interface"
  width={600}
  height={400}
  className="rounded-xl"
/>
```

---

## Accessibility Standard: WCAG 2.1 AA

Ravenbase targets **WCAG 2.1 Level AA** — the international standard required by
ADA (US), GDPR (EU), and EAA (European Accessibility Act). shadcn/ui components
implement most ARIA patterns correctly by default. The agent's responsibility is
to not break them and to implement the structural requirements below.

**WCAG 2.1 AA in numbers:**
- 4.5:1 minimum color contrast for body text (3:1 for large text and UI components)
- All interactive elements keyboard-accessible (Tab, Enter, Space, arrow keys, Escape)
- All images have descriptive `alt` text; decorative images use `alt=""`
- All form inputs have associated `<label>` elements
- Status messages announced to screen readers via `aria-live`
- Page language declared: `<html lang="en">`
- No keyboard traps (user can always exit any component with Escape or Tab)
- Skip navigation link at page start
- Heading hierarchy is logical (h1 → h2 → h3, never skipped)

### Required: Skip link to main content

Every page must have a skip link as the first focusable element. This lets keyboard
and screen reader users bypass navigation directly to the main content.

```tsx
// app/layout.tsx — insert as FIRST element inside <body>
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4
             focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground
             focus:rounded-md focus:font-medium focus:text-sm"
>
  Skip to main content
</a>
// ...
<main id="main-content">  {/* id must match href="#main-content" */}
  {children}
</main>
```

### Required: aria-live for streaming SSE content

When the agent streams tokens in the Chat and Workstation pages, the new content
must be announced to screen readers via an `aria-live` region.

```tsx
// In MemoryChat.tsx and MetaDocEditor.tsx:
<div
  aria-live="polite"      // polite: announces after user finishes current interaction
  aria-atomic="false"     // false: announces incremental additions, not the full buffer
  aria-label="AI response"
  className="..."
>
  {streamedContent}
</div>

// For status messages (ingestion progress, conflict resolution confirmations):
<div role="status" aria-live="polite" className="sr-only">
  {statusMessage}  {/* e.g. "File uploaded successfully. Processing started." */}
</div>
```

### Required: Focus management in modals and sheets

shadcn/ui Dialog and Sheet components handle focus trapping automatically.
Do NOT override their focus management. Key rules:

```tsx
// ✅ Correct: let shadcn manage focus
<Dialog>
  <DialogTrigger asChild><Button>Open</Button></DialogTrigger>
  <DialogContent>  {/* shadcn traps focus here, restores on close */}
    <DialogTitle>Resolve Conflict</DialogTitle>
    ...
  </DialogContent>
</Dialog>

// ❌ Never: override focus manually in Dialog/Sheet
// <Dialog onOpenChange={() => document.getElementById('my-input')?.focus()}>
// This breaks screen reader announcements

// When navigating between pages (not modal), focus the main heading:
import { useEffect, useRef } from "react"
export default function InboxPage() {
  const headingRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => { headingRef.current?.focus() }, [])
  return (
    <main>
      <h1 tabIndex={-1} ref={headingRef} className="focus:outline-none">
        Memory Inbox
      </h1>
      ...
    </main>
  )
}
```

### Color contrast verification

The Ravenbase design system already meets contrast requirements:
- `text-foreground` (#1a1a1a) on `bg-background` (#f5f3ee) = **12.3:1** ✓ (exceeds 4.5:1)
- `text-primary-foreground` (white) on `bg-primary` (#2d4a3e) = **8.1:1** ✓
- `text-muted-foreground` (#6b7280) on `bg-background` (#f5f3ee) = **4.6:1** ✓ (barely passes)

**Warning:** `text-muted-foreground` on `bg-card` (white) = **4.5:1** exactly — do not make it lighter.

If you add any custom color combination not listed above, verify contrast with:
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Or in DevTools: right-click any text → Inspect → check the contrast ratio in Styles panel

### Accessibility testing (run with every frontend story)

```bash
# Automated check via axe-core (catches ~40% of issues):
npm install -D @axe-core/playwright
# Add to your Playwright test:
import AxeBuilder from "@axe-core/playwright"
test("landing page has no critical accessibility violations", async ({ page }) => {
  await page.goto("/")
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze()
  expect(results.violations).toEqual([])
})

# Manual check (covers the 60% automated tools miss):
# Tab through every interactive element on the page
# Verify: (1) focus ring always visible, (2) logical order, (3) no keyboard traps
# Test with VoiceOver (Mac): Cmd+F5 to toggle. Navigate with VO+arrow keys.
```
