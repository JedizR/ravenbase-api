# STORY-039 — Critical Bug Fixes

> **Story ID:** STORY-039
> **Epic:** EPIC-10 — Production Launch
> **Type:** Frontend + Backend
> **Priority:** P0 — must complete before any deployment testing
> **Sprint:** 39

---

## Summary

Fix all P0 and high-priority P1 bugs that prevent the app from working end-to-end.
These bugs exist in the current codebase despite all 38 stories being "complete."
See `docs/components/REFACTOR_PLAN.md` for exact code changes per bug.

---

## Bugs Fixed in This Story

| Bug | File | Description |
|---|---|---|
| BUG-001 | app/(marketing)/page.tsx, privacy/page.tsx, terms/page.tsx | Header+Footer double-rendered |
| BUG-002 | app/(dashboard)/page.tsx (CREATE) | /dashboard returns 404 |
| BUG-003 | components/marketing/Header.tsx | backdrop-blur on scroll |
| BUG-004 | middleware.ts | Auth'd user at / not redirected |
| BUG-005 | components/domain/OnboardingWizard.tsx | Completion → /dashboard (404) |
| BUG-009 | ravenbase-api/Dockerfile.api | --reload flag in production |
| BUG-015 | app/(dashboard)/settings/data/page.tsx | Delete Account no API call |
| BUG-016 | components/domain/MetaDocEditor.tsx | Auto-save not implemented |
| BUG-017 | components/domain/MetaDocEditor.tsx | History click loads empty content |
| BUG-018 | app/(dashboard)/graph/GraphPageClient.tsx | Date range filter never applied |
| BUG-019 | app/(dashboard)/layout.tsx | No ErrorBoundary |
| BUG-020 | app/(dashboard)/layout.tsx | Missing skip link (WCAG) |
| BUG-022 | components/domain/MemoryChat.tsx | Stream reader leak on unmount |
| BUG-023 | app/(dashboard)/settings/notifications/page.tsx | Test email endpoint 404 |
| BUG-024 | app/(dashboard)/settings/data/page.tsx | Export status wrong URL |
| BUG-027 | components/marketing/PricingSection.tsx | "Open dashboard" links to 404 |
| BUG-028 | components/domain/MemoryInbox.tsx | activeIndex out of bounds |
| BUG-032 | contexts/ProfileContext.tsx | API cast without Zod validation |
| BUG-033 | components/marketing/PricingSection.tsx | Checkout URL not validated |

---

## Cross-references

- `docs/components/REFACTOR_PLAN.md` — exact code for every fix above
- `docs/components/FE-COMP-07-Workstation.md` — BUG-016, BUG-017 detail
- `docs/components/FE-COMP-06-GraphExplorer.md` — BUG-018 detail
- `docs/components/FE-COMP-05-MemoryInbox.md` — BUG-028 detail
- `docs/components/BE-COMP-05-AuthSystem.md` — BUG-004, BUG-005 detail

---

## Acceptance Criteria

- [ ] Landing page: exactly ONE header, ONE footer (BUG-001)
- [ ] /dashboard → 307 redirect to /chat (BUG-002)
- [ ] Header scrolled: solid `bg-background` (no `backdrop-blur`) (BUG-003)
- [ ] Authenticated user at `/` → redirected to `/chat` (BUG-004)
- [ ] Onboarding completion → `/chat` (BUG-005)
- [ ] `Dockerfile.api`: no `--reload`, has `--workers 2` (BUG-009)
- [ ] Delete Account: `DELETE /v1/account` fires before success toast (BUG-015)
- [ ] Workstation: auto-saves to `localStorage` every 30s (BUG-016)
- [ ] Workstation history click: `content_markdown` loaded, not empty (BUG-017)
- [ ] Graph date range filter: nodes actually filtered by date (BUG-018)
- [ ] Dashboard: component crash shows ErrorBoundary (not white screen) (BUG-019)
- [ ] Dashboard: skip link visible on keyboard Tab (BUG-020)
- [ ] MemoryChat: stream reader cancelled on component unmount (BUG-022)
- [ ] Notification test email: correct endpoint URL (BUG-023)
- [ ] Data export status: correct URL format (BUG-024)
- [ ] PricingSection: "Open dashboard" links to `/chat` (BUG-027)
- [ ] MemoryInbox: resolving last conflict shows ALL_CLEAR (no crash) (BUG-028)
- [ ] ProfileContext: validates API response with Zod (BUG-032)
- [ ] Checkout: URL validated before `window.location.href` redirect (BUG-033)
- [ ] `npm run build` → 0 TypeScript errors
- [ ] `make quality` → 0 ruff errors, 0 pyright errors
