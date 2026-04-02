# STORY-022: Pricing Page + Stripe Checkout

**Epic:** EPIC-07 — Marketing Site
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-018, STORY-023

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — Stripe checkout and pricing page story.

## Component
Marketing

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory)
> 2. `docs/design/CLAUDE_FRONTEND.md` — frontend rules (no form tags, Tailwind only, apiFetch)
> 3. `docs/design/01-design-system.md` — color tokens, card styles, button patterns
> 4. `docs/prd/05-monetization.md` — pricing tiers and credit costs
> 5. `docs/architecture/03-api-contract.md` — webhooks/stripe endpoint spec

---

## User Story
As a visitor, I want to understand the pricing tiers and subscribe to Pro so I can access full functionality.

## Context
- Design system: `design/01-design-system.md` — pricing card styles, CTA buttons
- Screen flows: `design/03-screen-flows.md` — route structure
- Monetization: `prd/05-monetization.md` — tier features and prices
- API contract: `architecture/03-api-contract.md` — `/webhooks/stripe` endpoint
- Auth: STORY-018 must be complete (Clerk integration needed for pre-filling email)
- Credits: STORY-023 must be complete (Stripe webhook updates User.tier)

## Acceptance Criteria
- [ ] AC-1: Pricing page at `/pricing` with Free, Pro ($15/mo), Team ($49/mo) tiers; annual toggle shows $12/mo and $39/mo respectively
- [ ] AC-2: Feature comparison table between tiers (file size limits, credit caps, profile count)
- [ ] AC-3: "Get Pro" button → Stripe Checkout session (pre-filled with user email from Clerk)
- [ ] AC-4: Stripe webhook: `checkout.session.completed` → update `User.tier = "pro"` in PostgreSQL
- [ ] AC-5: After successful payment: redirect to `/dashboard` with "Welcome to Pro!" toast
- [ ] AC-6: Annual billing toggle: Pro annual = $144/yr ($12/mo, save $36) vs $15/mo monthly; Team annual = $468/yr ($39/mo, save $120) vs $49/mo monthly
- [ ] AC-7: Stripe Customer Portal accessible from Settings → Billing (manage subscription, cancel)
- [ ] AC-8: Pricing page is light mode (route group `(marketing)/`), no auth required
- [ ] AC-9: Mobile-responsive: pricing cards stack vertically on < 768px
- [ ] AC-10: "Current plan" badge shown on active tier for logged-in users
- [ ] AC-11: Before processing any Stripe webhook, check Redis key `stripe:event:{event_id}` (TTL: 24 hours). If key exists: return `200 {"status": "already_processed"}` immediately — do not process again. Return `200` not `4xx` because Stripe retries on non-2xx responses, creating an infinite loop.
- [ ] AC-12: Redis event ID key is SET with 24-hour TTL only **after** the database write succeeds. If DB write fails: do NOT set the key (Stripe will retry and the event will be processed on next delivery).

## Technical Notes

### Files to Create (Frontend)
- `components/marketing/PricingSection.tsx` — pricing card grid
- `components/marketing/PricingToggle.tsx` — monthly/annual toggle
- `app/(marketing)/pricing/page.tsx` — full pricing page
- `app/(dashboard)/settings/billing/page.tsx` — Stripe Customer Portal link

### Files to Create (Backend)
- `src/api/routes/webhooks.py` — `POST /webhooks/stripe` handles `checkout.session.completed` and `customer.subscription.deleted`
- (If not already created in STORY-018): update `require_user` and `User` model

### Files to Modify (Backend)
- `src/models/user.py` — add `stripe_customer_id: Optional[str]` field
- `src/api/routes/credits.py` — add `POST /v1/billing/create-checkout-session` endpoint

### Architecture Constraints
- Stripe webhook signature MUST be validated using `stripe.Webhook.construct_event()`
- Never trust the `amount` from the webhook payload — look it up from Stripe API
- Stripe Checkout session must be created server-side (backend route), not client-side
- `User.tier` updated atomically with the webhook handler
- Light mode: `app/(marketing)/pricing/page.tsx` lives under `(marketing)/` route group

### Stripe Webhook Idempotency Pattern

```python
# POST /webhooks/stripe

async def handle_stripe_webhook(request: Request, redis: Redis, db: AsyncSession):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, request.headers["stripe-signature"], settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400)

    # Idempotency check — Stripe may deliver same event multiple times
    idempotency_key = f"stripe:event:{event['id']}"
    if await redis.exists(idempotency_key):
        log.info("stripe.webhook_duplicate", event_id=event["id"])
        return {"status": "already_processed"}  # ← MUST be 200, not 4xx

    # Process event
    try:
        if event["type"] == "checkout.session.completed":
            await _handle_checkout_completed(event["data"]["object"], db)
        # ... other event types
    except Exception as e:
        log.error("stripe.webhook_failed", event_id=event["id"], error=str(e))
        raise HTTPException(status_code=500)  # Tell Stripe to retry

    # Mark processed ONLY after successful DB write
    await redis.setex(idempotency_key, 86400, "1")
    return {"status": "processed"}
```

### Stripe Webhook Pattern
```python
# src/api/routes/webhooks.py
import stripe
from fastapi import Request, Header

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    raw_body = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            raw_body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"]["user_id"]
        # Update User.tier = "pro" in PostgreSQL
        ...
```

### Credit Costs Reference (for AC implementation)
- Free signup bonus: 500 credits
- Text ingest: 1 credit per 512-token chunk
- Meta-Doc (Haiku): 18 credits | Meta-Doc (Sonnet): 45 credits (Pro/Team only)
- Chat (Haiku): 3 credits | Chat (Sonnet): 8 credits (Pro/Team only)
- Pro top-up via Stripe: 1000 credits = $10

## Definition of Done
- [ ] Pricing page renders in light mode with 3 tiers
- [ ] Annual/monthly toggle changes displayed prices
- [ ] "Get Pro" triggers Stripe Checkout (test mode)
- [ ] Stripe webhook `checkout.session.completed` updates `User.tier` in DB (verify via psql)
- [ ] Settings → Billing shows Stripe Customer Portal link for Pro users
- [ ] `npm run build` passes (0 TypeScript errors)
- [ ] `make quality` passes (0 errors on webhook handler)

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
- Navigate to `/pricing` (no auth required)
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
# Frontend build check
npm run build

# Test Stripe webhook locally with Stripe CLI:
stripe listen --forward-to localhost:8000/webhooks/stripe

# Trigger a test payment event:
stripe trigger checkout.session.completed

# Verify user tier updated in DB:
uv run python -c "
from src.core.config import settings
import asyncpg, asyncio
async def check():
    conn = await asyncpg.connect(settings.DATABASE_URL)
    row = await conn.fetchrow('SELECT tier FROM users WHERE id = $1', 'YOUR_TEST_USER_ID')
    print(row)
asyncio.run(check())
"
```

**Passing result:** `tier = 'pro'` in the database after Stripe test event fires.

---

## Agent Implementation Brief

```
Implement STORY-022: Pricing Page + Stripe Checkout.

Read first:
1. CLAUDE.md (architecture rules)
2. docs/design/AGENT_DESIGN_PREAMBLE.md — NON-NEGOTIABLE visual rules, anti-patterns, and pre-commit checklist. Read fully before writing any JSX.
3. docs/design/00-brand-identity.md — logo spec, voice rules, mono label pattern
4. docs/design/01-design-system.md — all color tokens, typography
5. docs/design/CLAUDE_FRONTEND.md (frontend rules)
6. docs/prd/05-monetization.md (tier details and pricing)
7. docs/stories/EPIC-07-marketing/STORY-022.md (this file)

Key constraints:
- Pricing page is (marketing)/ route group — light mode, no auth required
- No <form> tags. All buttons use onClick handlers.
- Stripe Checkout session created server-side via backend route.
- Stripe webhook MUST validate signature via stripe.Webhook.construct_event().
- All styling via Tailwind classes only.

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
git add -A && git commit -m "feat(ravenbase): STORY-022 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-022"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-022
git add docs/stories/epics.md && git commit -m "docs: mark STORY-022 complete"
```
