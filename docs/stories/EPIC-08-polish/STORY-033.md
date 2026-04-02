# STORY-033: Legal Pages (Privacy Policy, Terms of Service, Cookie Consent)

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P0 (legal prerequisite — must be complete before first EU user or payment processor review)
**Complexity:** Small
**Depends on:** STORY-021 (marketing layout and footer must exist)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfies? -->
None — legal pages story (Privacy Policy, Terms of Service, Cookie Consent).

## Component
UI/Polish

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` (frontend rules — especially RULE 5: route groups don't force color mode, RULE 15: metadata required, RULE 16: skip links)
> 2. `docs/design/AGENT_DESIGN_PREAMBLE.md` — read every anti-pattern rejection before writing any JSX
> 3. `docs/design/01-design-system.md` — all CSS tokens, typography scale, radius scale
> 4. `docs/design/04-ux-patterns.md` — accessibility requirements
> 5. `docs/stories/EPIC-07-marketing/STORY-021.md` — marketing layout and footer to extend
> 6. `docs/stories/EPIC-08-polish/STORY-033.md` (this file)

---

## User Story

As a visitor about to sign up, I want to read Ravenbase's Privacy Policy so I can decide
whether to share my data.

As a paying customer, I want to read the Terms of Service so I understand the agreement.

As an EU user, I need to see a cookie consent notice before any tracking cookies are set.

## Context

**Why this is P0:** GDPR Article 13 requires a Privacy Policy to be linked and available before
collecting personal data (email address at registration). Without it, the registration form is
technically non-compliant. UK GDPR and Thailand PDPA have the same requirement. Stripe also
requires a linked Privacy Policy and Terms of Service before activating production payments.

**Scope of this story:** The story creates the page structure and placeholder copy. Legal copy
will be reviewed and finalized by a human before launch — the agent creates the correct
structure, not the final legal language.

**Cookie consent:** Ravenbase uses Clerk (essential auth cookies) and optionally PostHog
(analytics). Essential cookies are exempt from consent under GDPR. If PostHog is enabled
(`NEXT_PUBLIC_POSTHOG_KEY` is set), a consent banner is required before loading PostHog.

**Files already exist:** All three pages and the CookieConsent component already exist in the
filesystem. This is an AUDIT + FIX pass: verify existing files meet all ACs, fix only if broken.

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

### Files to Create (if missing — audit first)
- `app/(marketing)/privacy/page.tsx` — Privacy Policy page
- `app/(marketing)/terms/page.tsx` — Terms of Service page
- `components/marketing/CookieConsent.tsx` — Cookie consent banner (conditional on PostHog)

### Files to Modify (if needed after audit)
- `components/marketing/Footer.tsx` — add legal nav links
- `app/sitemap.ts` — verify `/privacy` and `/terms` are already included
- `app/(marketing)/layout.tsx` — add `<CookieConsent />` component

## Definition of Done
- [ ] `/privacy` and `/terms` pages render correctly with semantic structure
- [ ] Both pages appear in `app/sitemap.ts`
- [ ] Footer shows legal links in `<nav aria-label="Legal navigation">`
- [ ] Cookie consent banner shows only when PostHog is configured
- [ ] Placeholder copy sections clearly marked for human review before launch
- [ ] `npm run build` passes (0 TypeScript errors)
- [ ] Lighthouse: Accessibility > 95 on both pages

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
- Navigate to `/privacy` — confirm page renders correctly
- Navigate to `/terms` — confirm page renders correctly
- Confirm NO "Internal Server Error" or webpack runtime errors
- Confirm CSS loads correctly (no unstyled content)
- Open browser DevTools → Console tab
- Confirm no red errors (yellow warnings acceptable)

**Step 4 — Report one of:**
- ✅ `localhost verified` — pages render correctly
- ⚠️ `Issue found: [describe issue]` — fix before committing docs

Only commit the docs update (epics.md, story-counter, project-status, journal) AFTER localhost verification passes.

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

**Passing result:** Both legal pages render with Header + Footer, correct mono labels, semantic structure, skip links. CookieConsent shows only when PostHog is configured.

---

## Frontend Agent Brief

> **Skill Invocations — paste each skill call before starting that phase:**
>
> **Phase 1 (Read/Audit):** `Use /frontend-design — enforce production-grade aesthetic compliance`
> **Phase 2 (Verify existing files):** `Use /tailwindcss — for Tailwind CSS v4 token system`
> **Phase 3 (Fix/Enhance):** `Use /tailwindcss-advanced-layouts — for layout structure patterns`
> **Phase 4 (Accessibility):** `Use /tailwindcss-mobile-first — for mobile/accessibility verification`
> **Phase 5 (Final verification):** `Use /superpowers:verification-before-completion — before claiming done`

---

```
🎯 Target: Claude Code / MiniMax-M2.7 — Ultra-detailed step-by-step implementation prompt
💡 Optimized for: MiniMax-M2.7 — every function written out completely, zero "..." shortcuts
📋 Nature: AUDIT + FIX pass (files already exist). Verify all ACs, fix only broken items.

═══════════════════════════════════════════════════════════════════
STEP 0 — CONTEXT (carry forward to every phase)
═══════════════════════════════════════════════════════════════════

Ravenbase Frontend: Next.js 15 App Router + Tailwind CSS v4 + shadcn/ui
Design system: CSS variables only. Dark mode via .dark class on <html>
Brand colors: Primary=#2d4a3e (forest green), Background=#f5f3ee (warm cream)
AC-3: Legal pages are SSG — no "use client", no server-side data fetching
AC-7: CookieConsent is a "use client" component but only for localStorage state

═══════════════════════════════════════════════════════════════════
STEP 1 — READ PHASE (mandatory — read ALL files before touching code)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /frontend-design

Then read ALL files in this exact order:

1. CLAUDE.md
   → All 19 rules. Critical: RULE 5 (route groups), RULE 15 (metadata export),
     RULE 16 (skip links — first focusable element), RULE 17 (aria-live).

2. docs/design/AGENT_DESIGN_PREAMBLE.md
   → Anti-pattern automatic rejections:
     ❌ Hardcoded hex in JSX → must use CSS variable
     ❌ Rounded-lg on cards → must be rounded-2xl
     ❌ CookieConsent as <Dialog> → must be fixed bottom banner
     ❌ No metadata on marketing pages → required
     ❌ Missing skip link → required
     ❌ ◆ label without font-mono → must add

3. docs/design/01-design-system.md
   → All CSS tokens for :root and .dark
   → Typography: font-serif for h1/h2, font-mono for ◆ labels
   → Radius: rounded-2xl for cards, rounded-full for CTAs
   → Card: bg-card rounded-2xl border border-border

4. docs/design/04-ux-patterns.md
   → Accessibility requirements
   → Animation timings

5. docs/stories/EPIC-07-marketing/STORY-021.md
   → Marketing layout structure (Header + Footer)
   → Footer nav pattern

6. docs/stories/EPIC-08-polish/STORY-033.md (this file)
   → All 8 ACs. Implementation must satisfy all 8.

CONFIRMED READ: All 6 files read.

═══════════════════════════════════════════════════════════════════
STEP 2 — AUDIT EXISTING FILES (Phase 1 — run ALL commands before planning fixes)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss

Run these exact commands and record results for each:

A. Check if privacy page exists:
ls -la app/\(marketing\)/privacy/page.tsx
# Expected: file exists with non-zero size

B. Check if terms page exists:
ls -la app/\(marketing\)/terms/page.tsx
# Expected: file exists with non-zero size

C. Check if CookieConsent exists:
ls -la components/marketing/CookieConsent.tsx
# Expected: file exists with non-zero size

D. Check footer for legal nav links:
grep -n "aria-label.*Legal\|/privacy\|/terms" components/marketing/Footer.tsx
# Expected: output includes aria-label="Legal navigation" AND links to /privacy and /terms

E. Check sitemap for legal pages:
grep -n "privacy\|terms" app/sitemap.ts
# Expected: entries for both /privacy and /terms

F. Check marketing layout for CookieConsent placement:
grep -n "CookieConsent" app/\(marketing\)/layout.tsx
# Expected: import statement found

G. Check privacy page structure:
grep -n "font-serif\|aria-labelledby\|main-content\|skip" app/\(marketing\)/privacy/page.tsx
# Expected: font-serif on h1/h2, aria-labelledby on sections, id="main-content", skip link

H. Check terms page structure:
grep -n "font-serif\|aria-labelledby\|main-content\|skip" app/\(marketing\)/terms/page.tsx
# Expected: same structure as privacy page

I. Check CookieConsent component:
grep -n "use client\|NEXT_PUBLIC_POSTHOG_KEY\|ravenbase-cookie-consent" components/marketing/CookieConsent.tsx
# Expected: "use client", PostHog key check, localStorage key used

J. Check metadata on privacy page:
grep -n "metadata\|robots\|index" app/\(marketing\)/privacy/page.tsx
# Expected: export const metadata with robots: { index: true, follow: true }

Record ALL results. If any command returns unexpected output, that item must be fixed.

═══════════════════════════════════════════════════════════════════
STEP 3 — PRIVACY PAGE COMPLETE CODE (if creating or if audit found issues)
═══════════════════════════════════════════════════════════════════

If privacy page is MISSING or BROKEN — write this complete file:

FILE: app/(marketing)/privacy/page.tsx

"use server" is NOT needed. This is a Server Component (SSG).

```tsx
import type { Metadata } from "next"
import { Header } from "@/components/marketing/Header"
import { Footer } from "@/components/marketing/Footer"

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How Ravenbase collects, uses, and protects your personal data.",
  robots: { index: true, follow: true },
}

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Skip link — first focusable element (RULE 16) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4
                   focus:z-50 focus:px-4 focus:py-2 focus:bg-primary
                   focus:text-primary-foreground focus:rounded-md focus:font-medium
                   focus:text-sm"
      >
        Skip to main content
      </a>

      <Header />

      <main id="main-content" className="flex-1">
        <article className="max-w-3xl mx-auto px-6 py-16">
          {/* Page header */}
          <header className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-4">
              ◆ LEGAL
            </p>
            <h1 className="font-serif text-5xl leading-tight mb-4">
              Privacy Policy
            </h1>
            <p className="text-xs font-mono text-muted-foreground">
              Last updated: April 2026
            </p>
          </header>

          {/* Section 1: What We Collect */}
          <section aria-labelledby="what-we-collect" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ WHAT_WE_COLLECT
            </p>
            <h2 id="what-we-collect" className="font-serif text-2xl mb-4">
              What We Collect
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: describe account data (email, name, subscription tier),
                  content data (uploaded files, memory nodes, knowledge graph),
                  usage data (interaction logs, feature usage). */}
              Ravenbase collects information you provide directly, including your email
              address and name at registration, subscription tier and billing information
              at payment, and uploaded files, documents, and data you choose to process
              through the service. We also collect usage data including feature usage
              patterns, session duration, and interaction logs to improve service quality.
            </p>
          </section>

          {/* Section 2: How We Use It */}
          <section aria-labelledby="how-we-use-it" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ HOW_WE_USE_IT
            </p>
            <h2 id="how-we-use-it" className="font-serif text-2xl mb-4">
              How We Use It
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: service operation, AI processing, no sale of data. */}
              We use your data to operate and improve the Ravenbase service, process
              documents through our AI pipeline, generate knowledge graphs and meta-
              documents, detect conflicts in your memory store, and provide customer
              support. We do not sell, rent, or share your personal data with third
              parties for their marketing purposes.
            </p>
          </section>

          {/* Section 3: Data Retention */}
          <section aria-labelledby="data-retention" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ DATA_RETENTION
            </p>
            <h2 id="data-retention" className="font-serif text-2xl mb-4">
              Data Retention
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: retention periods, deletion procedures. */}
              We retain your personal data for as long as your account is active. Upon
              account deletion, we initiate a 30-day grace period during which you may
              contact support to recover your account. After this period, all personal
              data is permanently deleted from our systems within 90 days, except as
              required by applicable law.
            </p>
          </section>

          {/* Section 4: Your Rights */}
          <section aria-labelledby="your-rights" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ YOUR_RIGHTS
            </p>
            <h2 id="your-rights" className="font-serif text-2xl mb-4">
              Your Rights (GDPR/PDPA)
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: access, rectification, erasure, portability,
                  right to withdraw consent, right to lodge complaint. */}
              You have the right to access your personal data, rectify inaccurate data,
              request erasure of your data ("right to be forgotten"), receive your data
              in a portable format, withdraw consent at any time, and lodge a complaint
              with your local data protection authority. To exercise any of these rights,
              contact us at privacy@ravenbase.app or through the in-app support channel.
            </p>
          </section>

          {/* Section 5: Contact Us */}
          <section aria-labelledby="contact-us" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ CONTACT_US
            </p>
            <h2 id="contact-us" className="font-serif text-2xl mb-4">
              Contact Us
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: DPO contact, data controller info. */}
              Ravenbase is the data controller for processing your personal data. Our
              Data Protection Officer can be reached at dpo@ravenbase.app. For general
              privacy inquiries, contact privacy@ravenbase.app. Our registered office is
              located at [Registered Address], and we are registered with [DPA Name]
              under registration number [Registration Number].
            </p>
          </section>
        </article>
      </main>

      <Footer />
    </div>
  )
}
```

Note: No "use client" — this is a Server Component (SSG). No async data fetching.
All placeholder text is marked with comments for human review before launch.

═══════════════════════════════════════════════════════════════════
STEP 4 — TERMS PAGE COMPLETE CODE (if creating or if audit found issues)
═══════════════════════════════════════════════════════════════════

FILE: app/(marketing)/terms/page.tsx

```tsx
import type { Metadata } from "next"
import { Header } from "@/components/marketing/Header"
import { Footer } from "@/components/marketing/Footer"

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The agreement governing your use of the Ravenbase service.",
  robots: { index: true, follow: true },
}

export default function TermsPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Skip link — first focusable element (RULE 16) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4
                   focus:z-50 focus:px-4 focus:py-2 focus:bg-primary
                   focus:text-primary-foreground focus:rounded-md focus:font-medium
                   focus:text-sm"
      >
        Skip to main content
      </a>

      <Header />

      <main id="main-content" className="flex-1">
        <article className="max-w-3xl mx-auto px-6 py-16">
          {/* Page header */}
          <header className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-4">
              ◆ LEGAL
            </p>
            <h1 className="font-serif text-5xl leading-tight mb-4">
              Terms of Service
            </h1>
            <p className="text-xs font-mono text-muted-foreground">
              Last updated: April 2026
            </p>
          </header>

          {/* Section 1: Acceptance of Terms */}
          <section aria-labelledby="acceptance" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ ACCEPTANCE_OF_TERMS
            </p>
            <h2 id="acceptance" className="font-serif text-2xl mb-4">
              Acceptance of Terms
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: binding agreement, age requirement, continued use = acceptance. */}
              By creating a Ravenbase account or using the service, you agree to be bound
              by these Terms of Service and our Privacy Policy. You must be at least 18
              years old to use Ravenbase. If you do not agree to these terms, do not use
              the service. Continued use of the service following any changes to these
              terms constitutes your acceptance of the revised terms.
            </p>
          </section>

          {/* Section 2: Service Description */}
          <section aria-labelledby="service-description" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ SERVICE_DESCRIPTION
            </p>
            <h2 id="service-description" className="font-serif text-2xl mb-4">
              Service Description
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: document ingestion, AI processing, knowledge graph, conflicts. */}
              Ravenbase provides a permanent memory and knowledge management service that
              ingests documents, processes them through AI pipelines to extract entities
              and relationships, builds a knowledge graph, detects conflicts in stored
              information, and generates synthesized meta-documents. The service is provided
              as-is and availability may vary. We reserve the right to modify or discontinue
              features with 30 days notice.
            </p>
          </section>

          {/* Section 3: User Responsibilities */}
          <section aria-labelledby="user-responsibilities" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ USER_RESPONSIBILITIES
            </p>
            <h2 id="user-responsibilities" className="font-serif text-2xl mb-4">
              User Responsibilities
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: account security, lawful content, no misuse. */}
              You are responsible for maintaining the confidentiality of your account
              credentials and for all activity under your account. You agree to use
              Ravenbase only for lawful purposes and not to upload content that violates
              any third party's intellectual property rights, applicable law, or these
              terms. You may not reverse engineer, scrape, or misuse the service.
            </p>
          </section>

          {/* Section 4: Payment Terms */}
          <section aria-labelledby="payment-terms" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ PAYMENT_TERMS
            </p>
            <h2 id="payment-terms" className="font-serif text-2xl mb-4">
              Payment Terms
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: subscription billing, cancellation, refunds. */}
              Subscription fees are billed in advance on a monthly or annual basis
              depending on your chosen plan. All fees are non-refundable except as
              required by applicable law. You may cancel your subscription at any time
              through the account settings page; cancellation takes effect at the end of
              the current billing period. We reserve the right to change pricing with
              30 days notice prior to your next billing cycle.
            </p>
          </section>

          {/* Section 5: Limitation of Liability */}
          <section aria-labelledby="limitation" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ LIMITATION_OF_LIABILITY
            </p>
            <h2 id="limitation" className="font-serif text-2xl mb-4">
              Limitation of Liability
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: as-is service, no warranty, liability cap. */}
              Ravenbase is provided "as is" without warranties of any kind. We do not
              guarantee the accuracy, completeness, or reliability of any processed
              content or AI-generated output. To the maximum extent permitted by law,
              our total liability for any claim arising from your use of the service
              shall not exceed the amounts paid by you to Ravenbase in the 12 months
              preceding the claim. We are not liable for any indirect, incidental, or
              consequential damages.
            </p>
          </section>

          {/* Section 6: Governing Law */}
          <section aria-labelledby="governing-law" className="mb-12">
            <p className="text-xs font-mono text-muted-foreground tracking-wider mb-2">
              ◆ GOVERNING_LAW
            </p>
            <h2 id="governing-law" className="font-serif text-2xl mb-4">
              Governing Law
            </h2>
            <p className="text-muted-foreground leading-relaxed">
              {/* Placeholder: jurisdiction, dispute resolution. */}
              These Terms of Service are governed by the laws of [Jurisdiction],
              without regard to conflict of law principles. Any dispute arising from
              these terms or your use of Ravenbase shall be resolved exclusively in
              the courts of [Jurisdiction]. Before initiating any legal action, you
              agree to contact us and attempt to resolve the dispute informally within
              30 days.
            </p>
          </section>
        </article>
      </main>

      <Footer />
    </div>
  )
}
```

═══════════════════════════════════════════════════════════════════
STEP 5 — COOKIE CONSENT COMPONENT COMPLETE CODE (if creating or fixing)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-advanced-layouts

FILE: components/marketing/CookieConsent.tsx

```tsx
"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"

const CONSENT_KEY = "ravenbase-cookie-consent"

export function CookieConsent() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    // AC-7a: only show if PostHog is configured
    const hasPostHog = !!process.env.NEXT_PUBLIC_POSTHOG_KEY
    // AC-7b: only show if consent not yet given
    const hasConsent = localStorage.getItem(CONSENT_KEY) !== null
    setVisible(hasPostHog && !hasConsent)
  }, [])

  if (!visible) return null

  const accept = () => {
    localStorage.setItem(CONSENT_KEY, "accepted")
    setVisible(false)
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
      className="fixed bottom-0 left-0 right-0 z-50
                 bg-card border-t border-border p-4
                 shadow-lg"
    >
      <div className="max-w-3xl mx-auto flex flex-col sm:flex-row items-center gap-4">
        <div className="flex-1 text-center sm:text-left">
          <p
            id="cookie-consent-title"
            className="text-sm font-medium text-foreground mb-1"
          >
            Cookie preferences
          </p>
          <p
            id="cookie-consent-desc"
            className="text-xs text-muted-foreground leading-relaxed"
          >
            We use analytics cookies to improve Ravenbase. Essential cookies
            (authentication) are always active.{" "}
            <Link
              href="/privacy"
              className="underline hover:text-foreground transition-colors"
            >
              Privacy Policy
            </Link>
            .
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Button
            size="sm"
            onClick={accept}
            className="rounded-full bg-primary text-primary-foreground
                       hover:bg-primary/90 transition-colors
                       min-h-[44px] px-6"
          >
            Accept
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={decline}
            className="rounded-full border-border hover:bg-secondary
                       min-h-[44px] px-6"
          >
            Decline
          </Button>
        </div>
      </div>
    </div>
  )
}
```

AC-7 verification:
- (a) `NEXT_PUBLIC_POSTHOG_KEY` check: `!!process.env.NEXT_PUBLIC_POSTHOG_KEY` — line 14
- (b) localStorage key `ravenbase-cookie-consent`: lines 16, 28, 32
- (c) PostHog loads only after consent: this is enforced in the analytics integration (separate file checks localStorage before initializing PostHog)
- (d) Accept and Decline buttons: lines 25-26 (accept), lines 30-31 (decline)
- (e) Link to Privacy Policy: lines 22-24

PLACEMENT: In app/(marketing)/layout.tsx, add:
```tsx
import { CookieConsent } from "@/components/marketing/CookieConsent"

// Inside the layout component, after <Header /> and before {children}:
<CookieConsent />
```

═══════════════════════════════════════════════════════════════════
STEP 6 — FOOTER LEGAL NAV (verify and fix if needed)
═══════════════════════════════════════════════════════════════════

Read components/marketing/Footer.tsx.

Find the existing `<nav>` element or create a new one inside the footer.
The legal nav links must be in `<nav aria-label="Legal navigation">`.

If missing, add this inside the footer, near the bottom:

```tsx
<nav aria-label="Legal navigation" className="flex gap-4 text-xs text-muted-foreground">
  <Link href="/privacy" className="hover:text-foreground transition-colors">
    Privacy Policy
  </Link>
  <Link href="/terms" className="hover:text-foreground transition-colors">
    Terms of Service
  </Link>
</nav>
```

Verify with:
grep -n "aria-label.*Legal" components/marketing/Footer.tsx
# Expected: 1 (the aria-label on the legal nav)

grep -n "/privacy\|/terms" components/marketing/Footer.tsx
# Expected: at least 2 (one for each link)

═══════════════════════════════════════════════════════════════════
STEP 7 — SITEMAP VERIFICATION (AC-3)
═══════════════════════════════════════════════════════════════════

grep -n "privacy\|terms" app/sitemap.ts
# Expected: entries for both /privacy and /terms

If missing, add to app/sitemap.ts:
{ url: `${base}/privacy`, lastModified: new Date(), changeFrequency: "yearly", priority: 0.3 },
{ url: `${base}/terms`, lastModified: new Date(), changeFrequency: "yearly", priority: 0.3 },

═══════════════════════════════════════════════════════════════════
STEP 8 — ACCESSIBILITY VERIFICATION PLAN
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-mobile-first

For BOTH /privacy and /terms pages, verify:

□ Skip link: first focusable element in DOM (after <body>)
   grep -n "href=\"#main-content\"" app/\(marketing\)/privacy/page.tsx
   # Expected: 1 (skip link present)

□ Skip link: href="#main-content", targets id="main-content" on <main>
   grep -n "id=\"main-content\"" app/\(marketing\)/privacy/page.tsx
   # Expected: 1

□ <main id="main-content"> exists exactly once per page
   grep -c "id=\"main-content\"" app/\(marketing\)/privacy/page.tsx
   # Expected: 1

□ <article> contains all section content
   grep -c "<article>" app/\(marketing\)/privacy/page.tsx
   # Expected: 1

□ Heading hierarchy: h1 → h2 (never skipped levels)
   grep -n "<h1\|<h2\|<h3" app/\(marketing\)/privacy/page.tsx
   # Expected: h1 first, then only h2 throughout

□ All sections have aria-labelledby pointing to their h2 id
   grep -n "aria-labelledby" app/\(marketing\)/privacy/page.tsx
   # Expected: 1 per section (5 total)

□ Metadata export: robots: { index: true, follow: true }
   grep -A2 "robots:" app/\(marketing\)/privacy/page.tsx
   # Expected: index: true, follow: true

□ Font check: h1 and h2 use className="font-serif"
   grep -n "font-serif" app/\(marketing\)/privacy/page.tsx | grep -v "text-xs"
   # Expected: h1 and h2 have font-serif

□ Mono labels: ◆ prefix in text-xs font-mono text-muted-foreground tracking-wider
   grep -n "◆ " app/\(marketing\)/privacy/page.tsx
   # Expected: 6 (one per page header + one per section)

□ CookieConsent role="dialog" with aria-labelledby and aria-describedby
   grep -n "role=\"dialog\"" components/marketing/CookieConsent.tsx
   # Expected: 1

□ CookieConsent has aria-labelledby and aria-describedby
   grep -n "aria-labelledby\|aria-describedby" components/marketing/CookieConsent.tsx
   # Expected: 2

□ CookieConsent buttons have min-h-[44px] (AC-8: 44px touch target)
   grep -n "min-h-\[44px\]" components/marketing/CookieConsent.tsx
   # Expected: 2 (one per button)

═══════════════════════════════════════════════════════════════════
STEP 9 — AC VERIFICATION TABLE (Phase 5 — final check before claiming done)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /superpowers:verification-before-completion

For each AC, write a one-line verification result:

□ AC-1: privacy page exists with semantic structure (article, h1-h3)
   grep -c "font-serif text-5xl" app/\(marketing\)/privacy/page.tsx
   Expected: 1
   Result: ____

□ AC-2: terms page exists with semantic structure
   grep -c "font-serif text-5xl" app/\(marketing\)/terms/page.tsx
   Expected: 1
   Result: ____

□ AC-3: sitemap includes /privacy and /terms
   grep -E "privacy|terms" app/sitemap.ts | wc -l
   Expected: >= 2
   Result: ____

□ AC-4: footer has legal nav with aria-label
   grep -c "aria-label.*Legal" components/marketing/Footer.tsx
   Expected: 1
   Result: ____

□ AC-5: privacy page has 5 sections with ◆ mono labels
   grep -c "◆ " app/\(marketing\)/privacy/page.tsx
   Expected: >= 6 (1 page header + 5 sections)
   Result: ____

□ AC-6: terms page has 6 sections with ◆ mono labels
   grep -c "font-serif text-2xl" app/\(marketing\)/terms/page.tsx
   Expected: 6
   Result: ____

□ AC-7a: CookieConsent is client component
   grep -c '"use client"' components/marketing/CookieConsent.tsx
   Expected: 1
   Result: ____

□ AC-7b: CookieConsent checks PostHog key
   grep -c "NEXT_PUBLIC_POSTHOG_KEY" components/marketing/CookieConsent.tsx
   Expected: 1
   Result: ____

□ AC-7c: CookieConsent uses correct localStorage key
   grep -c "ravenbase-cookie-consent" components/marketing/CookieConsent.tsx
   Expected: >= 3 (constant defined + accept + decline + maybe check)
   Result: ____

□ AC-8: privacy metadata exports robots index
   grep -A2 "robots:" app/\(marketing\)/privacy/page.tsx
   Expected: index: true
   Result: ____

□ Brand: pages use bg-background (not bg-white)
   grep -c "bg-background" app/\(marketing\)/privacy/page.tsx
   Expected: >= 1
   Result: ____

□ Brand: no hardcoded hex colors
   grep -rn "#2d4a3e\|#f5f3ee\|#ffffff" app/\(marketing\)/privacy/page.tsx components/marketing/CookieConsent.tsx
   Expected: 0 (only acceptable in CSS variable definitions in globals.css)
   Result: ____

□ Accessibility: skip link on privacy page
   grep -c "href=\"#main-content\"" app/\(marketing\)/privacy/page.tsx
   Expected: 1
   Result: ____

□ Accessibility: skip link on terms page
   grep -c "href=\"#main-content\"" app/\(marketing\)/terms/page.tsx
   Expected: 1
   Result: ____

□ CookieConsent placement in marketing layout
   grep -c "CookieConsent" app/\(marketing\)/layout.tsx
   Expected: >= 1
   Result: ____

═══════════════════════════════════════════════════════════════════
ANTI-PATTERNS — automatic rejection without asking
═══════════════════════════════════════════════════════════════════

❌ className="bg-white" in any component → must be bg-card or bg-background
❌ className="rounded-lg" on any card → must be rounded-2xl
❌ CookieConsent as <Dialog> or <Modal> → must be fixed bottom banner
❌ No metadata export on /privacy or /terms → required for SEO (AC-3, AC-8)
❌ Marketing pages using "use client" for content → SSG server components
❌ CookieConsent checking localStorage without "use client" directive
❌ Hardcoded hex color in className string → must use CSS variable
❌ Footer legal links without aria-label="Legal navigation"
❌ Page without skip link as first focusable element

═══════════════════════════════════════════════════════════════════
SUCCESS CRITERIA — ALL must be YES to report complete
═══════════════════════════════════════════════════════════════════

✅ npm run build passes (0 TypeScript errors)
✅ AC-1 through AC-8 all verified
✅ Skip link present on both /privacy and /terms pages
✅ <main id="main-content"> exactly once on both pages
✅ All headings use font-serif
✅ All ◆ mono labels use font-mono
✅ CookieConsent: fixed bottom banner (not modal)
✅ CookieConsent: "use client" directive present
✅ CookieConsent: PostHog key check present
✅ CookieConsent: localStorage key correct
✅ Footer: aria-label="Legal navigation" with both links
✅ Both pages in sitemap.ts
✅ No hardcoded hex colors in component files
✅ CookieConsent buttons: min-h-[44px] touch targets

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
