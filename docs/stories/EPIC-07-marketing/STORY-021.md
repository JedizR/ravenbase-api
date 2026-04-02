# STORY-021: Landing Page

**Epic:** EPIC-07 — Marketing Site
**Priority:** P1
**Complexity:** Large
**Depends on:** STORY-018 (auth routes must exist for CTA to link to)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — marketing landing page story.

## Component
Marketing

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (Tailwind only, no form tags, apiFetch)
> 3. `docs/design/00-brand-identity.md` — Ravenbase brand identity, tone, tagline
> 4. `docs/design/01-design-system.md` — full token system, typography, mono label pattern
> 5. `docs/design/03-screen-flows.md` — landing page section layout

---

## User Story
As a visitor, I want to understand what Ravenbase does within 10 seconds so I decide to sign up.

## Context
- Design system: `design/01-design-system.md` — full token system
- Brand: `design/00-brand-identity.md`
- Template components: adapted from WebUI_template.txt (Typewriter → Ravenbase)

## Acceptance Criteria
- [ ] AC-1: Sections in order: Header → Hero → How It Works → Features (3-column grid) → Feature Deep-Dive (2 alternating sections) → Testimonials → FAQ → CTA → Footer — matches the layout spec in `docs/design/03-screen-flows.md` (FAQ added between Testimonials and CTA as an objection-handler before the conversion CTA)
- [ ] AC-2: Hero: `"What happened, where, and when. Always."` headline in Playfair Display; subheadline below: "Years of scattered notes → one structured memory"; animated knowledge graph mockup (~40 nodes, force-directed SVG); **two CTA buttons**: primary `[Start for free →]` (links to `/register`) and secondary `[Watch demo]` (links to `#how-it-works` section anchor)
- [ ] AC-3: How It Works: 3-step workflow (Upload → Build Graph → Generate)
- [ ] AC-4: Features: Memory Inbox card, Meta-Documents card, Knowledge Graph card
- [ ] AC-5: All CTAs link to `/register`
- [ ] AC-6: Mobile-responsive (all sections adapt correctly at 375px)
- [ ] AC-7: Lighthouse CI: score > 90 on Performance, Accessibility, Best Practices, SEO (mobile)
- [ ] AC-8: Framer Motion scroll animations on feature cards (staggered reveal)
- [ ] AC-9: Mono label pattern from design system used throughout (`◆ MEMORY_GRAPH`, `◆ SYSTEM_MODULES`)
- [ ] AC-10: Root `app/layout.tsx` uses `next/font` for DM Sans, Playfair Display, and JetBrains Mono — no `@import` from Google Fonts in globals.css
- [ ] AC-11: Root `app/layout.tsx` exports `metadata` with `metadataBase: new URL("https://ravenbase.app")`, full OG and Twitter card tags
- [ ] AC-12: `app/sitemap.ts` exists and returns the 4 public marketing routes (index, pricing, privacy, terms); dashboard routes excluded
- [ ] AC-13: `app/robots.ts` exists and disallows crawling of `/dashboard/`, `/api/`, `/sign-in`, `/sign-up`
- [ ] AC-14: `app/(marketing)/page.tsx` includes JSON-LD SoftwareApplication structured data via `<Script type="application/ld+json">`
- [ ] AC-15: Landing page HTML uses semantic landmarks: `<header>` for site nav, `<main>` for page content, `<section>` for each content block with `aria-labelledby`, `<footer>` for legal links — zero layout `<div>` wrappers where a semantic element is appropriate
- [ ] AC-16: All images on the landing page use `<Image>` from `next/image`; hero image uses `priority` prop
- [ ] AC-17: Feature Deep-Dive section: 2 alternating left/right sections below the 3-column features grid. Section 1: Memory Inbox product mockup (left) + explanatory copy (right). Section 2: explanatory copy (left) + Meta-Documents product mockup (right). Each section has a `◆ FEATURE_NAME` mono label, a benefit-focused h3, and 2–3 sentences of copy. Images use `<Image>` from `next/image`. Section uses `aria-labelledby` on a visually hidden h2 for accessibility.
- [ ] AC-18: Testimonials section (◆ HALL_OF_RECORDS): 3 testimonial cards in a responsive grid. Each card uses the system-aesthetic naming convention from `docs/design/03-screen-flows.md`: identifier codes `REF-0088`, `REF-2301`, `REF-7725`. Each card has a short quote, the identifier code in JetBrains Mono, and a role/context string. Placeholder copy pre-filled — clearly marked with `// TODO: replace with real testimonials before launch` comment in the component. Section uses `<section aria-labelledby="testimonials-heading">` with a visually hidden heading.
- [ ] AC-19: FAQ section: 4 questions in a collapsible accordion (shadcn/ui `Accordion` component). Questions address the top visitor objections: (1) "Is my data private and secure?" (2) "How is this different from ChatGPT's memory feature?" (3) "How much does it cost?" (4) "Do I need technical skills to use Ravenbase?" Answers are 1–3 sentences each. Section uses `<section aria-labelledby="faq-heading">`.

## Technical Notes

### Files to Create (Frontend)
- `components/marketing/Header.tsx`
- `components/marketing/HeroSection.tsx`
- `components/marketing/WorkflowSection.tsx`
- `components/marketing/FeaturesSection.tsx`
- `components/marketing/FeatureDeepDive.tsx` — alternating left/right product screenshots
- `components/marketing/TestimonialsSection.tsx` — 3 REF-XXXX placeholder cards
- `components/marketing/FAQSection.tsx` — shadcn Accordion, 4 questions
- `components/marketing/CTASection.tsx`
- `components/marketing/Footer.tsx`
- `app/(marketing)/page.tsx` — uses `(marketing)` route group (light mode forced)

### Additional Package Required
```bash
npm install framer-motion
```

### Architecture Constraints
- Landing page is light mode by default — no forced className on the layout (RULE 9: no forced color mode in route groups)
- No `<form>` tags on the page — CTA buttons are `<Link href="/register">` anchors
- All components in `components/marketing/` — separate from dashboard `components/domain/`
- No `apiFetch` calls on landing page — it's fully static (no auth required)
- Framer Motion `viewport={{ once: true }}` on scroll animations — animate only once

### Mono Label Pattern
```tsx
// Design system mono label — use throughout landing page
<span className="text-xs font-mono text-muted-foreground tracking-wider uppercase">
  ◆ MEMORY_GRAPH
</span>
```

### Hero Section Pattern
```tsx
// components/marketing/HeroSection.tsx
"use client";
import { motion } from "framer-motion";
import Link from "next/link";

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center px-6">
      <div className="max-w-4xl mx-auto text-center space-y-8">
        <motion.span
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xs font-mono text-muted-foreground tracking-wider"
        >
          ◆ RAVENBASE
        </motion.span>
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="font-serif text-5xl md:text-7xl font-bold leading-tight"
        >
          What happened, where,
          <br />
          and when. Always.
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-lg text-muted-foreground max-w-xl mx-auto"
        >
          Years of scattered notes → one structured memory
        </motion.p>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <Link
            href="/register"
            className="inline-flex items-center justify-center px-8 py-4 bg-primary text-primary-foreground rounded-full font-medium hover:opacity-90 transition-opacity"
          >
            Start for free →
          </Link>
          <a
            href="#how-it-works"
            className="inline-flex items-center justify-center px-8 py-4 border border-border text-foreground rounded-full font-medium hover:bg-muted transition-colors"
          >
            Watch demo
          </a>
        </motion.div>
      </div>
    </section>
  );
}
```

### Scroll Animation Pattern (feature cards)
```tsx
// In FeaturesSection.tsx — staggered reveal
const cards = [
  { title: "Memory Inbox", description: "...", mono: "◆ CONFLICT_RESOLUTION" },
  { title: "Meta-Documents", description: "...", mono: "◆ AI_GENERATION" },
  { title: "Knowledge Graph", description: "...", mono: "◆ MEMORY_GRAPH" },
];

{cards.map((card, i) => (
  <motion.div
    key={card.title}
    initial={{ opacity: 0, y: 30 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ delay: i * 0.15 }}
    className="p-6 border rounded-xl space-y-4"
  >
    <span className="text-xs font-mono text-muted-foreground">{card.mono}</span>
    <h3 className="text-xl font-semibold">{card.title}</h3>
    <p className="text-muted-foreground">{card.description}</p>
  </motion.div>
))}
```

### SEO Technical Requirements

The landing page is the primary SEO surface for Ravenbase. Read `docs/design/CLAUDE_FRONTEND.md`
→ "SEO Specification" section before implementing. Key requirements:

**File tree additions required:**
```
app/
├── layout.tsx          ← metadataBase + next/font + html lang="en"
├── sitemap.ts          ← built-in Next.js, auto-served at /sitemap.xml
├── robots.ts           ← built-in Next.js, auto-served at /robots.txt
└── (marketing)/
    └── page.tsx        ← metadata export + JSON-LD Script + semantic HTML
```

**No external packages needed.** `sitemap.ts` and `robots.ts` are built into
Next.js 15 App Router — they are special files, not route handlers.

**`next/font` replaces Google Fonts `@import`:** When you implement STORY-001-WEB
scaffolding (Sprint 18), you will move all font imports from `globals.css` to
`app/layout.tsx` using `next/font/google`. The CSS variables (`--font-sans`,
`--font-serif`, `--font-mono`) remain the same — only the loading mechanism changes.

**Dashboard noindex:** In `app/(dashboard)/layout.tsx`, add:
```tsx
export const metadata: Metadata = { robots: { index: false, follow: false } }
```

**Validation after implementation:**
```bash
# 1. Check /sitemap.xml renders correctly:
curl http://localhost:3000/sitemap.xml

# 2. Check /robots.txt:
curl http://localhost:3000/robots.txt

# 3. Validate JSON-LD with Google's tool:
# Paste your page URL into: https://search.google.com/test/rich-results
# OR paste the JSON-LD directly. Expect: "SoftwareApplication" eligible result.

# 4. Lighthouse SEO audit (must score > 90):
npx lighthouse http://localhost:3000 --only-categories=seo --form-factor=mobile
```

## Definition of Done
- [ ] All 9 sections render correctly on desktop and 375px mobile: Header, Hero (dual CTA), How It Works, Features (3-col), Feature Deep-Dive (2 alternating), Testimonials (3 cards), FAQ (4 questions), CTA, Footer
- [ ] Hero has dual CTA: primary "Start for free →" links to /register; secondary "Watch demo" scrolls to #how-it-works
- [ ] Framer Motion scroll animations working with viewport={{ once: true }}
- [ ] Mono label pattern used in all sections
- [ ] Testimonials cards use REF-XXXX aesthetic; FAQ accordion uses shadcn Accordion
- [ ] Lighthouse mobile: Performance > 90, Accessibility > 95
- [ ] `npm run build` passes

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
- Navigate to `/` (landing page — no auth required)
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
# 1. Open http://localhost:3000 (landing page)
# 2. Verify sections in order: Header → Hero → How It Works → Features (3-col) → Feature Deep-Dive (2 alternating) → Testimonials (3 REF-XXXX cards) → FAQ (4 accordion questions) → CTA → Footer
# 2b. Verify hero has TWO buttons: "Start for free →" links to /register; "Watch demo" scrolls to #how-it-works
# 3. Verify hero headline is "What happened, where, and when. Always." in Playfair Display
# 4. Scroll down — verify staggered animation on feature cards
# 5. Click any CTA — verify redirects to /register
# 6. Resize to 375px — verify all sections adapt correctly
# 7. Open DevTools Lighthouse — run mobile audit
#    Expected: Performance > 90, Accessibility > 95

# Lighthouse CLI check (optional):
npx lighthouse http://localhost:3000 --only-categories=performance,accessibility,best-practices,seo --form-factor=mobile
```

**Passing result:** Landing page renders all 7 sections. Framer Motion animations play on scroll. CTAs link to /register. Lighthouse mobile > 90.

---

## Agent Implementation Brief

```
Implement STORY-021: Landing Page.

Read first:
1. CLAUDE.md (architecture rules)
2. docs/design/AGENT_DESIGN_PREAMBLE.md — NON-NEGOTIABLE visual rules, anti-patterns, and pre-commit checklist. Read fully before writing any JSX.
3. docs/design/00-brand-identity.md — logo spec, voice rules, mono label pattern
4. docs/design/01-design-system.md — all color tokens, typography
5. docs/design/CLAUDE_FRONTEND.md (Tailwind only, no form tags)
6. docs/design/03-screen-flows.md (landing page section layout)
7. docs/stories/EPIC-07-marketing/STORY-021.md (this file)

Key constraints:
- Install: npm install framer-motion
- Landing page is light by default — no className="light" on layout (RULE 9)
- No apiFetch or auth on landing page — fully static
- No <form> tags — all CTAs are <Link href="/register"> anchors or <a href="#anchor"> scroll links
- Framer Motion viewport={{ once: true }} on scroll animations
- Mono label pattern: text-xs font-mono tracking-wider ◆ LABEL_NAME
- 9 sections total: Header, Hero (dual CTA), How It Works, Features (3-col), Feature Deep-Dive (2 alternating), Testimonials (3 REF-XXXX cards, placeholder copy), FAQ (shadcn Accordion, 4 questions), CTA, Footer
- Hero has TWO buttons: primary "Start for free →" → /register; secondary "Watch demo" → #how-it-works
- FAQSection.tsx uses shadcn <Accordion> component — do not build a custom accordion
- TestimonialsSection.tsx: placeholder copy marked with // TODO comment; REF-XXXX aesthetic per screen flows
- FeatureDeepDive.tsx: alternating left/right layout per docs/design/03-screen-flows.md

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
git add -A && git commit -m "feat(ravenbase): STORY-021 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-021"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-021
git add docs/stories/epics.md && git commit -m "docs: mark STORY-021 complete"
```
