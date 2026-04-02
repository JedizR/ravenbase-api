# PricingPage

> **Component ID:** FE-COMP-02
> **Epic:** EPIC-07 — Marketing Site
> **Stories:** STORY-022
> **Type:** Frontend (Marketing Site)

---

## Purpose

The Pricing Page converts visitors to paid subscribers. It presents three clear pricing tiers (Free, Pro, Team) with transparent feature differentiation, an annual/monthly toggle showing savings, and a frictionless path to Stripe Checkout. It lives at `/pricing` — Header and Footer injected by `app/(marketing)/layout.tsx`. Admin users see an access bypass message instead of tier cards.

---

## User Journey

**Unauthenticated user:**
1. Visits `/pricing` → sees 3 tier cards (Free, Pro, Team)
2. Annual/monthly toggle → prices update instantly (client-side only)
3. Clicks "Get Pro" → middleware detects no auth → redirect to `/login?redirect_url=/pricing`
4. After login → back to `/pricing`
5. Clicks "Get Pro" (now authed) → `POST /v1/billing/create-checkout-session {tier: "pro", annual: false}`
6. Backend returns `{checkout_url: "https://checkout.stripe.com/..."}`
7. URL validated (must start with `https://checkout.stripe.com/`), then `window.location.href = checkout_url`
8. User pays → Stripe sends `checkout.session.completed` webhook
9. Backend: `user.tier = "pro"`, `credits_balance += 2000`, log `CreditTransaction`
10. Stripe redirects to: `APP_BASE_URL/settings/billing?checkout=success`
11. Frontend shows toast: "You're now on Pro!"

**Authenticated user (already subscribed):**
1. Visits `/pricing`
2. `GET /v1/me` response shows `tier: "pro"` → Pro card gets "Current Plan" badge
3. "Open dashboard" CTA on current tier → links to `/chat` (NOT `/dashboard` — BUG-027)
4. Clicking "Manage Subscription" → `GET /v1/billing/portal` → redirects to Stripe Customer Portal

**Admin user:**
1. Visits `/pricing`
2. `GET /v1/me` returns `{is_admin: true}`
3. Tier cards replaced with admin bypass message (no Stripe CTAs)

---

## Subcomponents

```
app/(marketing)/pricing/
  page.tsx               — Pricing page (SSG + client hydration for toggle/auth state)
  loading.tsx            — Skeleton while auth/user data loads

components/marketing/
  PricingSection.tsx     — Orchestrator: toggle + tier cards + admin bypass
  PricingToggle.tsx      — Annual/monthly toggle switch (BUG-012: bg-white → bg-secondary)
  PricingCard.tsx        — Individual tier card (Free/Pro/Team)
  PricingComparison.tsx  — Feature comparison table below cards
  StripeCheckoutButton.tsx — Handles checkout session API call + redirect
```

---

## API Contracts

```
POST /v1/billing/create-checkout-session
  Request:  { tier: "pro" | "team", annual: boolean }
  Response: { checkout_url: string }
  Auth:     Required
  Security: ALWAYS validate response URL starts with "https://checkout.stripe.com/" before redirect (BUG-033)
  On error: toast.error("Failed to start checkout. Please try again.")

GET /v1/billing/portal
  Response: { portal_url: string }
  Auth:     Required
  Used by:  "Manage subscription" for existing subscribers

GET /v1/me
  Response: { id, email, tier: "free"|"pro"|"team", credits_balance, is_admin: boolean }
  Auth:     Required (if authed — skip for unauthenticated visitors)
  Used by:  Detect admin users, highlight current plan
```

---

## Admin Bypass

If `GET /v1/me` returns `is_admin: true`, replace tier cards with:

```tsx
{user?.is_admin ? (
  <div className="text-center py-12 bg-card border border-border rounded-2xl p-8">
    <p className="font-mono text-xs text-muted-foreground tracking-wider">◆ ADMIN_ACCOUNT</p>
    <p className="font-serif text-2xl mt-3">Full access bypass active</p>
    <p className="text-muted-foreground mt-2">All features unlocked. Credits disabled.</p>
  </div>
) : (
  <div className="grid md:grid-cols-3 gap-6">
    {TIERS.map(tier => <PricingCard key={tier.name} {...tier} />)}
  </div>
)}
```

No Stripe interaction occurs for admin users. Backend credit bypass is independent (via `ADMIN_USER_IDS`).

---

## Design System Rules

Cross-reference: `docs/design/AGENT_DESIGN_PREAMBLE.md` (READ FIRST)
Cross-reference: `docs/design/01-design-system.md` (tokens)

Specific rules:
- **Toggle background:** `bg-secondary` (`#e8ebe6`) — NEVER `bg-white` (BUG-012: `PricingToggle.tsx:33`)
- **Popular tier border:** `border-2 border-primary` (`#2d4a3e`)
- **Other tier borders:** `border border-border rounded-2xl`
- **Card background:** `bg-card` (white elevated surface on cream background)
- **CTA buttons:** `rounded-full` — never `rounded-md`
- **"Open dashboard" link:** `href="/chat"` — never `href="/dashboard"` (BUG-027)
- **Price text:** `font-bold text-4xl` for amount, `text-muted-foreground` for `/mo`

---

## Known Bugs / Current State

**BUG-012 (MEDIUM):** `PricingToggle.tsx:33` hardcodes `bg-white` — design system violation.
- **Fix:** Change `bg-white` → `bg-secondary`
- **Story:** STORY-039

**BUG-027 (HIGH):** "Open dashboard" CTA links to `/dashboard` → 404 for logged-in users.
- **Root cause:** `components/marketing/PricingSection.tsx:278` uses `href="/dashboard"`.
- **Fix:** Change all `/dashboard` hrefs in PricingSection to `/chat`.
- **Story:** STORY-039

**BUG-033 (MEDIUM):** Checkout URL not validated before redirect.
- **Root cause:** `components/marketing/PricingSection.tsx:145-150` does `window.location.href = data.checkout_url` without checking the URL.
- **Fix:** Add URL validation: `if (!checkout_url.startsWith("https://checkout.stripe.com/")) { toast.error(...); return; }`
- **Story:** STORY-039

---

## Acceptance Criteria

- [ ] `/pricing` → 200 OK, 3 tier cards: Free ($0), Pro ($15), Team ($49)
- [ ] Annual toggle → Pro shows $12/mo, Team shows $39/mo, savings displayed
- [ ] Pro tier card: `border-2 border-primary` (highlighted as most popular)
- [ ] `PricingToggle` uses `bg-secondary` background (never `bg-white`)
- [ ] Unauthenticated user "Get Pro" → redirects to `/login?redirect_url=/pricing`
- [ ] Authenticated user "Get Pro" → `POST /v1/billing/create-checkout-session` fires
- [ ] Non-Stripe checkout URL → `toast.error`, NO redirect
- [ ] Authenticated Pro subscriber: "Open dashboard" → `/chat` (not 404)
- [ ] Admin user → sees admin bypass message, no tier cards, no Stripe CTAs
- [ ] Mobile (375px): cards stack vertically, full-width

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `docs/design/01-design-system.md` — tokens for toggle, card borders
- `BE-COMP-06-CreditSystem.md` — credit grant on tier upgrade (2000 for Pro, 6000 for Team)
- `docs/architecture/03-api-contract.md` — billing and me endpoints
- `docs/components/REFACTOR_PLAN.md` — BUG-012, BUG-027, BUG-033 fix details

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-022](../stories/EPIC-07-marketing/STORY-022.md) | Pricing Page + Stripe Checkout | Cross-repo | Tiers, toggle, Stripe Checkout, webhook |

---

## Product Requirements

1. **Three Pricing Tiers:**
   - **Free:** $0/mo — 500 credits/mo, 10 source uploads, 10 Meta-Docs/mo, 3 profiles, Haiku only
   - **Pro:** $15/mo ($12/mo annual = $144/yr) — 2,000 credits/mo, unlimited uploads/Meta-Docs, 20 profiles, Haiku + Sonnet
   - **Team:** $49/mo ($39/mo annual = $468/yr) — 6,000 shared credits, everything Pro + cross-user graph sharing (3 seats)

2. **Annual/Monthly Toggle:** Switches displayed prices. Annual shows savings: Pro saves $36/yr, Team saves $120/yr.

3. **Feature Comparison Table:** Below the cards: file size limits (50MB free / 200MB pro), credit caps, profile limits, model access.

4. **Stripe Checkout:** Backend creates checkout session via `POST /v1/billing/create-checkout-session`. Returns pre-filled Stripe Checkout URL. **Always validate URL before redirect.**

5. **Stripe Webhook:** `POST /webhooks/stripe` handles `checkout.session.completed` → updates `User.tier`. Includes Redis idempotency key.

6. **Post-Payment Redirect:** After successful payment → `/settings/billing?checkout=success` with toast.

---

## Component Files

```
app/(marketing)/pricing/
  page.tsx             — Full pricing page

components/marketing/
  PricingToggle.tsx    — Monthly/annual toggle switch
  PricingCard.tsx      — Individual tier card
  PricingComparison.tsx — Feature comparison table
  StripeCheckoutButton.tsx — Handles checkout session creation
```

## Stripe Checkout Flow

```tsx
// StripeCheckoutButton.tsx — with URL validation fix for BUG-033
const handleCheckout = async () => {
  try {
    const { checkout_url } = await apiFetch<{ checkout_url: string }>(
      "/v1/billing/create-checkout-session",
      { method: "POST", body: JSON.stringify({ tier: selectedTier, annual: isAnnual }) }
    )
    // BUG-033 fix: validate URL before redirect
    if (!checkout_url.startsWith("https://checkout.stripe.com/")) {
      toast.error("Invalid checkout URL received. Please try again.")
      return
    }
    window.location.href = checkout_url
  } catch {
    toast.error("Failed to start checkout. Please try again.")
  }
}
```

## Webhook Idempotency

```python
# POST /webhooks/stripe idempotency pattern
idempotency_key = f"stripe:event:{event['id']}"
if await redis.exists(idempotency_key):
    return {"status": "already_processed"}  # 200, not 4xx
# ... process event ...
await redis.setex(idempotency_key, 86400, "1")  # 24h TTL
return {"status": "processed"}
```
