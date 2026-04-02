# LandingPage

> **Component ID:** FE-COMP-01
> **Epic:** EPIC-07 — Marketing Site
> **Stories:** STORY-021
> **Type:** Frontend (Marketing Site)

---

## Purpose

The Landing Page is the primary SEO surface and first impression for Ravenbase. It converts unauthenticated visitors to registered users through a structured narrative flow (Hero → How It Works → Features → Testimonials → FAQ → CTA), backed by a fully static Next.js SSG page. The page renders under `app/(marketing)/` — Header and Footer are injected by `app/(marketing)/layout.tsx` and must NOT be imported again inside `page.tsx`.

---

## User Journey

**Unauthenticated visitor:**
1. Arrives at `/` from Google / referral / direct link
2. Sees Hero → How It Works → Features → Testimonials → FAQ → Final CTA
3. Clicks "Start for free →" → `/register`
4. Completes Clerk sign-up → webhook fires → backend creates User + 500 credits
5. `/register` page has `afterSignUpUrl="/onboarding"` (component prop, overrides env var)
6. Redirected to `/onboarding` → OnboardingWizard
7. Completes onboarding → `/chat`

**Authenticated returning user:**
1. Visits `/`
2. `middleware.ts` detects `userId` → redirects immediately to `/chat`
3. Never sees the landing page content (BUG-004 means this is currently broken — fix in STORY-039)

---

## Subcomponents

```
app/(marketing)/
  page.tsx                   — Full page composing all sections (NO Header/Footer import here)
  sitemap.ts                 — 4 marketing routes
  robots.ts                  — Disallow /api/, /chat, /inbox, /graph, /sources, /workstation

components/marketing/
  Header.tsx                 — Site nav: logo + nav links + auth CTAs (rendered by layout)
  HeroSection.tsx            — Headline, subheadline, animated SVG graph, 2 CTAs
  WorkflowSection.tsx        — "How It Works" 3-step: Upload → Build Graph → Generate
  FeaturesSection.tsx        — 3-column features grid with mono labels
  FeatureDeepDive.tsx        — 2 alternating left/right detail sections
  TestimonialsSection.tsx    — 3 REF-XXXX placeholder cards (BUG-014: needs real testimonials)
  FAQSection.tsx             — shadcn Accordion, 4 questions
  CTASection.tsx             — Bottom CTA with "Start for free →"
  PricingToggle.tsx          — Annual/monthly toggle (used on /pricing, not landing page)
  Footer.tsx                 — Legal links + social (rendered by layout)
```

---

## API Contracts

None. Landing page is fully static (SSG). No API calls at render time.

Auth redirect uses `auth()` from `@clerk/nextjs/server` — a server-side function that reads the Clerk session cookie, not an API call.

```typescript
// app/(marketing)/page.tsx — SSG with auth redirect
import { auth } from "@clerk/nextjs/server"
import { redirect } from "next/navigation"

export default async function HomePage() {
  const { userId } = await auth()
  if (userId) redirect("/chat")  // BUG-004: currently missing — fix in STORY-039
  return <LandingPageContent />
}
```

---

## Admin Bypass

Not applicable. Landing page requires no auth and calls no APIs. Admin users visiting `/` are redirected to `/chat` by the auth check (same as all authenticated users).

---

## Design System Rules

Cross-reference: `docs/design/AGENT_DESIGN_PREAMBLE.md` (READ FIRST before writing any JSX)
Cross-reference: `docs/design/00-brand-identity.md` (hero copy, brand voice)
Cross-reference: `docs/design/01-design-system.md` (all color tokens)

Specific rules for this component:
- **Header on scroll:** `bg-background border-b border-border shadow-sm` — NO `backdrop-blur-sm` or `bg-background/95` (BUG-003)
- **Page background:** `bg-background` = `#f5f3ee` warm cream (never `bg-white`)
- **Hero headline:** `font-serif text-5xl md:text-6xl lg:text-7xl` (Playfair Display)
- **Primary CTA:** `rounded-full bg-primary text-primary-foreground` (bg-primary = `#2d4a3e`)
- **Secondary CTA:** `rounded-full variant="outline"`
- **Section mono labels:** `font-mono text-xs tracking-wider text-muted-foreground` with `◆` prefix
- **Feature cards:** `bg-card border border-border rounded-2xl p-6`
- **Testimonial cards:** `bg-card border border-border rounded-2xl p-6`
- **Footer and Header:** Rendered ONLY in `app/(marketing)/layout.tsx` — never in `page.tsx` or sub-pages (BUG-001)
- **PricingToggle background:** Must use `bg-secondary` (never `bg-white`) — BUG-012 in PricingToggle.tsx:33
- **"How it works" nav link:** Only valid on `/` — should not appear on `/pricing` or `/terms` (BUG-013)

---

## Known Bugs / Current State

**BUG-001 (HIGH):** Header and Footer render twice on `/`, `/privacy`, `/terms`.
- **Root cause:** `app/(marketing)/layout.tsx` renders `<Header>` and `<Footer>` for all children. Each page file (`page.tsx`, `privacy/page.tsx`, `terms/page.tsx`) ALSO imports and renders them independently.
- **Fix:** Remove `Header` + `Footer` imports and JSX from individual page files. Layout handles them.
- **Files:** `app/(marketing)/page.tsx`, `app/(marketing)/privacy/page.tsx`, `app/(marketing)/terms/page.tsx`
- **Story:** STORY-039

**BUG-003 (MEDIUM):** Header uses `backdrop-blur-sm` on scroll — design system violation.
- **Root cause:** `components/marketing/Header.tsx:36` has `"bg-background/95 backdrop-blur-sm border-b border-border shadow-sm"` in the scrolled state className.
- **Fix:** Change to `"bg-background border-b border-border shadow-sm"` — solid background, no blur, no transparency.
- **Story:** STORY-039

**BUG-004 (MEDIUM):** Authenticated users visiting `/` see the landing page instead of being redirected to `/chat`.
- **Root cause:** `middleware.ts` only redirects unauthenticated users away from protected routes. It has no branch that redirects authenticated users from `/` to `/chat`.
- **Fix:** Add `if (userId && pathname === "/") redirect("/chat")` to `middleware.ts`.
- **Story:** STORY-039

**BUG-012 (MEDIUM):** `PricingToggle.tsx:33` has `bg-white` hardcoded — design system violation.
- **Fix:** Change `bg-white` → `bg-secondary` (= `#e8ebe6`).
- **Story:** STORY-039

**BUG-013 (MEDIUM):** "How it works" nav link is broken on `/pricing` and `/terms`.
- **Root cause:** The `#how-it-works` anchor only exists on the landing page. Clicking from other pages scrolls to top (no target).
- **Fix:** In `components/marketing/Header.tsx` NAV_LINKS, only show "How it works" link when on `/` route. On other pages, link to `/#how-it-works` to navigate to the landing page section.
- **Story:** STORY-039

**BUG-014 (HIGH — LAUNCH BLOCKER):** TestimonialsSection has placeholder fake testimonials with `// TODO: replace with real testimonials` comment. Cannot launch with fake social proof.
- **Fix:** Remove placeholder testimonials OR replace with real beta tester quotes.
- **File:** `components/marketing/TestimonialsSection.tsx`
- **Story:** STORY-039 (placeholder removal) or STORY-043 (real testimonials)

---

## Acceptance Criteria

- [ ] `GET /` → 200 OK, exactly ONE nav bar, ONE footer visible
- [ ] Scroll down landing page → header stays solid (no blur, no transparency)
- [ ] Landing page has all 9 sections in correct order (Hero → FAQ → CTA)
- [ ] Hero has two CTAs: "Start for free →" (links to `/register`) and "Watch demo" (scrolls to `#how-it-works`)
- [ ] Hero headline text: "What happened, where, and when. Always." in Playfair Display
- [ ] All section labels use `◆ MONO_LABEL` pattern with `font-mono text-xs tracking-wider`
- [ ] FAQ accordion: click each question → answer expands and collapses
- [ ] Mobile (375px): all sections adapt, no horizontal overflow
- [ ] Authenticated user visits `/` → immediately redirects to `/chat` (not landing page)
- [ ] Unauthenticated user visits `/chat` → redirects to `/login`
- [ ] `npm run build` → 0 TypeScript errors
- [ ] `GET /sitemap.xml` → lists `/`, `/pricing`, `/privacy`, `/terms`
- [ ] `GET /robots.txt` → disallows `/api/`, authenticated routes

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `docs/design/00-brand-identity.md` — hero copy, tone, brand voice
- `docs/design/01-design-system.md` — all color tokens, typography scale
- `docs/design/02-component-library.md` — shadcn/ui base component usage
- `FE-COMP-02-PricingPage.md` — PricingSection is shared between landing and pricing page
- `docs/architecture/03-api-contract.md` — no API calls here, but cross-check redirect paths
- `docs/components/REFACTOR_PLAN.md` — BUG-001, BUG-003, BUG-004, BUG-012, BUG-013, BUG-014 fix details

---

## Product Requirements

1. **Page Structure (top to bottom):** Header → Hero → How It Works → Features (3-column grid) → Feature Deep-Dive (2 alternating sections) → Testimonials → FAQ → CTA → Footer

2. **Hero Section:** Headline: "What happened, where, and when. Always." in Playfair Display. Subheadline: "Years of scattered notes → one structured memory". Animated knowledge graph mockup (~40 nodes, force-directed SVG). Two CTAs: primary "Start for free →" (links to `/register`), secondary "Watch demo" (scrolls to `#how-it-works`).

3. **How It Works Section:** 3-step workflow: Upload → Build Graph → Generate. Each step shown with icon + label.

4. **Features Grid:** 3-column grid: Memory Inbox card, Meta-Documents card, Knowledge Graph card. Each card uses mono label pattern (`◆ CONFLICT_RESOLUTION`, `◆ AI_GENERATION`, `◆ MEMORY_GRAPH`).

5. **Feature Deep-Dive Sections:** Two alternating left/right sections below the grid. Section 1: Memory Inbox product mockup (left) + explanatory copy (right). Section 2: Meta-Documents mockup (right) + explanatory copy (left). Each section has a `◆ FEATURE_NAME` mono label, benefit-focused h3, and 2–3 sentences.

6. **Testimonials Section:** `◆ HALL_OF_RECORDS` mono label. 3 testimonial cards in responsive grid. System-aesthetic naming: `REF-0088`, `REF-2301`, `REF-7725`. Each card: short quote, identifier in JetBrains Mono, role/context string. **NOTE: Current placeholder content must be replaced before launch (BUG-014).**

7. **FAQ Section:** 4 questions in shadcn/ui Accordion.

8. **CTA Section:** "Start building your second brain today." with primary "Start for free →" CTA.

9. **Footer:** Links to Privacy Policy, Terms of Service, Pricing. Social links.

10. **SEO Requirements:** `metadataBase` set in root layout, full OG + Twitter card tags, JSON-LD SoftwareApplication structured data, `sitemap.xml` and `robots.txt`, semantic HTML landmarks.

11. **Performance:** All images via `next/image` with `priority` on hero. `next/font` for all typefaces (no Google Fonts `@import`). Framer Motion scroll animations with `viewport={{ once: true }}`.

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-021](../stories/EPIC-07-marketing/STORY-021.md) | Landing Page | Frontend | Full landing page with all 9 sections |

---

## Component Files

```
components/marketing/
  Header.tsx           — Site nav with logo + links
  HeroSection.tsx      — Hero with animated graph mockup
  WorkflowSection.tsx  — How It Works (Upload → Build Graph → Generate)
  FeaturesSection.tsx  — 3-column features grid
  FeatureDeepDive.tsx  — 2 alternating left/right sections
  TestimonialsSection.tsx — 3 REF-XXXX placeholder cards
  FAQSection.tsx       — shadcn Accordion, 4 questions
  CTASection.tsx       — CTA with primary button
  Footer.tsx            — Legal links + social

app/
  (marketing)/page.tsx  — Full page composing all sections
  sitemap.ts            — 4 marketing routes
  robots.ts             — Disallow dashboard routes
```

## Visual Patterns

### Hero Animation (CSS/Framer Motion)
The animated graph mockup is a simplified SVG force-directed visualization (~40 nodes) showing Concept and Memory nodes connected by edges. Use CSS animation or a lightweight Framer Motion variant — NOT full Cytoscape (too heavy for landing page).

```tsx
// Simplified animated graph — decorative only, not interactive
<div className="relative w-full h-96">
  <svg viewBox="0 0 800 400" className="w-full h-full">
    {nodes.map((node, i) => (
      <motion.circle
        key={node.id}
        cx={node.x}
        cy={node.y}
        r={node.type === "concept" ? 12 : 8}
        fill={node.type === "concept" ? "var(--primary)" : "var(--accent)"}
        animate={{ cx: node.x + Math.sin(i) * 20, cy: node.y + Math.cos(i) * 20 }}
        transition={{ repeat: Infinity, duration: 3 + i * 0.5, yoyo: true }}
      />
    ))}
  </svg>
</div>
```

### Testimonial Card Pattern
```tsx
<article className="bg-card border border-border rounded-2xl p-6 space-y-4">
  <blockquote className="text-foreground italic">
    "Ravenbase changed how I think about my knowledge."
  </blockquote>
  <footer className="flex items-center justify-between">
    <div>
      <p className="text-sm font-medium font-mono">REF-0088</p>
      <p className="text-xs text-muted-foreground">Knowledge Manager · Tech Co.</p>
    </div>
  </footer>
</article>
```
