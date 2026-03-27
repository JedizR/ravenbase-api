# STORY-033: Legal Pages (Privacy Policy, Terms of Service, Cookie Consent)

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P0 (legal prerequisite — must be complete before first EU user or payment processor review)
**Complexity:** Small
**Depends on:** STORY-021 (marketing layout and footer must exist)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — legal pages story (Privacy Policy, Terms of Service, Cookie Consent).

## Component
UI/Polish

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` (frontend rules — RULE 5: route groups don't force color mode)
> 2. `docs/design/CLAUDE_FRONTEND.md` — SEO spec (legal pages are SSG, indexable)
> 3. `docs/stories/EPIC-07-marketing/STORY-021.md` — marketing layout and footer to extend

---

## User Story
As a visitor about to sign up, I want to read Ravenbase's Privacy Policy so I can decide whether to share my data.
As a paying customer, I want to read the Terms of Service so I understand the agreement.
As an EU user, I need to see a cookie consent notice before any tracking cookies are set.

## Context
**Why this is P0:** GDPR Article 13 requires a Privacy Policy to be linked and available before collecting personal data (email address at registration). Without it, the registration form is technically non-compliant. UK GDPR and Thailand PDPA have the same requirement. Stripe also requires a linked Privacy Policy and Terms of Service before activating production payments.

**Scope of this story:** The story creates the page structure and placeholder copy. Legal copy will be reviewed and finalized by a human before launch — the agent creates the correct structure, not the final legal language.

**Cookie consent:** Ravenbase uses Clerk (essential auth cookies) and optionally PostHog (analytics). Essential cookies are exempt from consent under GDPR. If PostHog is enabled (`NEXT_PUBLIC_POSTHOG_KEY` is set), a consent banner is required before loading PostHog.

## Acceptance Criteria
- [ ] AC-1: `app/(marketing)/privacy/page.tsx` exists and renders at `/privacy` with a `<main>` element containing an `<article>` with headings h1-h3 in logical order
- [ ] AC-2: `app/(marketing)/terms/page.tsx` exists and renders at `/terms` with the same semantic structure
- [ ] AC-3: Both pages are statically generated (SSG), included in `app/sitemap.ts`, and export correct `metadata` with title and description
- [ ] AC-4: The marketing layout footer (`components/marketing/Footer.tsx`) has visible links to `/privacy` and `/terms` in a `<nav aria-label="Legal navigation">` element
- [ ] AC-5: Privacy Policy page includes these sections as h2 headings: "What We Collect", "How We Use It", "Data Retention", "Your Rights (GDPR/PDPA)", "Contact Us" — with placeholder copy under each
- [ ] AC-6: Terms of Service page includes these sections as h2 headings: "Acceptance of Terms", "Service Description", "User Responsibilities", "Payment Terms", "Limitation of Liability", "Governing Law" — with placeholder copy under each
- [ ] AC-7: A cookie consent banner component exists (`components/marketing/CookieConsent.tsx`) that: (a) shows only if `NEXT_PUBLIC_POSTHOG_KEY` is set, (b) stores consent in localStorage key `ravenbase-cookie-consent`, (c) only loads PostHog after consent is given, (d) has Accept and Decline buttons, (e) links to the Privacy Policy
- [ ] AC-8: The Privacy Policy page exports metadata with `robots: { index: true, follow: true }` so it is crawlable by Google (required for trust signals)

## Technical Notes

### Files to Create
- `app/(marketing)/privacy/page.tsx` — Privacy Policy page
- `app/(marketing)/terms/page.tsx` — Terms of Service page
- `components/marketing/CookieConsent.tsx` — Cookie consent banner (conditional on PostHog)

### Files to Modify
- `components/marketing/Footer.tsx` — add legal nav links
- `app/sitemap.ts` — verify `/privacy` and `/terms` are already included (they should be from STORY-021)
- `app/(marketing)/layout.tsx` — add `<CookieConsent />` component

### Page Structure Pattern

```tsx
// app/(marketing)/privacy/page.tsx
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How Ravenbase collects, uses, and protects your personal data.",
  robots: { index: true, follow: true },
}

export default function PrivacyPolicy() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-16">
      <article>
        <header className="mb-12">
          <p className="text-xs font-mono text-muted-foreground tracking-wider mb-4">
            ◆ LEGAL
          </p>
          <h1 className="font-serif text-5xl leading-tight mb-4">Privacy Policy</h1>
          <p className="text-muted-foreground">
            Last updated: {/* Update this date before launch */}
          </p>
        </header>

        <section aria-labelledby="what-we-collect">
          <h2 id="what-we-collect" className="font-serif text-2xl mt-12 mb-4">
            What We Collect
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            {/* Placeholder: describe account data, content data, usage data */}
          </p>
        </section>

        <section aria-labelledby="how-we-use-it">
          <h2 id="how-we-use-it" className="font-serif text-2xl mt-12 mb-4">
            How We Use It
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            {/* Placeholder: describe service operation, AI processing, no sale of data */}
          </p>
        </section>

        {/* Additional sections following same pattern:
            Data Retention, Your Rights (GDPR/PDPA), Contact Us */}
      </article>
    </main>
  )
}
```

### Cookie Consent Component

```tsx
// components/marketing/CookieConsent.tsx
"use client"
import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

const CONSENT_KEY = "ravenbase-cookie-consent"

export function CookieConsent() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // Only show if PostHog is configured AND consent not yet given
    const hasPostHog = !!process.env.NEXT_PUBLIC_POSTHOG_KEY
    const hasConsent = localStorage.getItem(CONSENT_KEY) !== null
    setVisible(hasPostHog && !hasConsent)
  }, [])

  if (!visible) return null

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, "accepted")
    setVisible(false)
    // PostHog will be loaded on next page navigation after consent
    // (check localStorage before initializing PostHog in analytics.tsx)
  }

  const decline = () => {
    localStorage.setItem(CONSENT_KEY, "declined")
    setVisible(false)
  }

  return (
    <div
      role="dialog"
      aria-labelledby="cookie-consent-title"
      aria-describedby="cookie-consent-desc"
      className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-sm
                 z-50 bg-card border border-border rounded-2xl p-5 shadow-lg"
    >
      <p id="cookie-consent-title" className="font-medium text-sm mb-2">
        Cookie preferences
      </p>
      <p id="cookie-consent-desc" className="text-xs text-muted-foreground mb-4 leading-relaxed">
        We use analytics cookies to improve Ravenbase. Essential cookies (authentication)
        are always active. See our{" "}
        <Link href="/privacy" className="underline hover:text-foreground">
          Privacy Policy
        </Link>
        .
      </p>
      <div className="flex gap-2">
        <Button size="sm" onClick={accept} className="flex-1">Accept</Button>
        <Button size="sm" variant="outline" onClick={decline} className="flex-1">Decline</Button>
      </div>
    </div>
  )
}
```

### Architecture Constraints
- Legal pages are 100% static (SSG) — no server-side data fetching
- Cookie consent must NOT use `useSearchParams` or any dynamic data — pure client state
- Placeholder copy must be clearly marked with `{/* Placeholder: ... */}` comments so a human knows what to fill in
- The cookie consent banner must NOT block page interaction (fixed bottom, not modal)
- PostHog must never initialize if consent is `"declined"` or absent

## Definition of Done
- [ ] `/privacy` and `/terms` pages render correctly with semantic structure
- [ ] Both pages appear in `app/sitemap.ts`
- [ ] Footer shows legal links in `<nav aria-label="Legal navigation">`
- [ ] Cookie consent banner shows only when PostHog is configured
- [ ] Placeholder copy sections clearly marked for human review before launch
- [ ] `npm run build` passes (0 TypeScript errors)
- [ ] Lighthouse: Accessibility > 95 on both pages

## Testing This Story

```bash
npm run build  # Must pass
npm run dev

# Verify pages render:
curl http://localhost:3000/privacy | grep "Privacy Policy"
curl http://localhost:3000/terms | grep "Terms of Service"

# Verify sitemap includes legal pages:
curl http://localhost:3000/sitemap.xml | grep "privacy"
curl http://localhost:3000/sitemap.xml | grep "terms"

# Verify footer links:
curl http://localhost:3000 | grep "/privacy"

# Cookie consent test:
# 1. Set NEXT_PUBLIC_POSTHOG_KEY=test_key in .env.local
# 2. Open http://localhost:3000 in browser
# 3. Verify banner appears
# 4. Click Accept → verify localStorage.getItem("ravenbase-cookie-consent") === "accepted"
# 5. Refresh → verify banner does not reappear
```

---

## Agent Implementation Brief

```
Implement STORY-033: Legal Pages (Privacy Policy, Terms of Service, Cookie Consent).

Read first:
1. CLAUDE.md (frontend rules — especially RULE 5: route groups, RULE 15: metadata export)
2. docs/design/CLAUDE_FRONTEND.md (SEO spec, semantic HTML rules)
3. docs/stories/EPIC-07-marketing/STORY-021.md (marketing layout and footer to extend)
4. docs/stories/EPIC-08-polish/STORY-033.md (this file)

Key constraints:
- Both pages must be SSG (no async data fetching) — pure static content
- Cookie consent: client component only, conditional on NEXT_PUBLIC_POSTHOG_KEY
- Never block page with modal — use fixed bottom banner
- Placeholder copy clearly marked with comments — do not write real legal language

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

```bash
npm run build && npm run test
git add -A && git commit -m "feat(ravenbase): STORY-033 legal pages and cookie consent"
git push
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-033
git add docs/stories/epics.md docs/.bmad/project-status.md
git commit -m "docs: mark STORY-033 complete"
git push
```
