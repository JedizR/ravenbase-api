# STORY-041 — Sources Page Upload + UX Gaps + Deployment Config

> **Story ID:** STORY-041
> **Epic:** EPIC-10 — Production Launch
> **Type:** Frontend
> **Priority:** P1 — must complete before production launch
> **Sprint:** 41
> **DEPENDS ON:** STORY-039

---

## Summary

Wire the existing `IngestionDropzone` component into the Sources page Upload tab, fix miscellaneous UX gaps, create deployment configuration files (`vercel.json`, fix `next.config.mjs`), and clean up remaining P1/P2 bugs.

---

## Work Items

| Item | File | Description |
|---|---|---|
| UX-001 | app/(dashboard)/sources/page.tsx | Wire IngestionDropzone into Upload tab |
| UX-002 | hooks/use-theme.ts | Verify dark mode writes .dark to <html> |
| UX-003 | components/marketing/HeroSection.tsx | Verify dual CTA exists |
| DEPLOY-001 | ravenbase-web/vercel.json (CREATE) | Security headers + /dashboard redirect |
| DEPLOY-002 | ravenbase-web/next.config.mjs | Add image remotePatterns |
| BUG-010 | ravenbase-web/vercel.json | Same as DEPLOY-001 |
| BUG-012 | components/marketing/PricingToggle.tsx | bg-white → bg-secondary |
| BUG-013 | components/marketing/Header.tsx | Fix "How it works" nav link |
| BUG-014 | components/marketing/TestimonialsSection.tsx | Remove fake testimonials |
| BUG-021 | components/domain/Omnibar.tsx | Remove /search and /generate from CommandList |
| BUG-025 | components/domain/GraphQueryBar.tsx | Example clicks auto-execute |
| BUG-026 | app/admin/page.tsx | Progress bar design system fix |
| BUG-029 | app/(dashboard)/settings/profiles/page.tsx | Profile color CSS var fix |
| BUG-030 | app/(dashboard)/settings/profiles/page.tsx | Remove duplicate color |
| BUG-031 | app/(dashboard)/settings/loading.tsx | Fix skeleton structure |

---

## Cross-references

- `docs/components/REFACTOR_PLAN.md` — UX-001 through UX-003, DEPLOY-001, DEPLOY-002, BUG-012 through BUG-031 exact code

---

## Acceptance Criteria

- [ ] `/sources` Upload tab: shows `IngestionDropzone` (not "File upload coming soon") (UX-001)
- [ ] Drop a PDF → upload starts → source appears in list after processing (UX-001)
- [ ] Dark mode toggle: `.dark` class applied to `document.documentElement` (UX-002)
- [ ] HeroSection: two CTAs visible — primary "Start for free →" + secondary "How it works" (UX-003)
- [ ] `vercel.json` created with security headers (X-Frame-Options, X-Content-Type-Options, etc.) (DEPLOY-001)
- [ ] `next.config.mjs`: `remotePatterns` includes `img.clerk.com`, `*.supabase.co` (DEPLOY-002)
- [ ] PricingToggle: no `bg-white` class (BUG-012)
- [ ] "How it works" nav link navigates correctly on all pages (BUG-013)
- [ ] No fake testimonials rendered on landing page (BUG-014)
- [ ] Omnibar command list: only `/ingest` and `/profile` shown (BUG-021)
- [ ] GraphQueryBar example clicks: fill input AND auto-execute query (BUG-025)
- [ ] `npm run build` → 0 TypeScript errors
