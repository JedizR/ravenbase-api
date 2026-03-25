# STORY-023: Credits System

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-016

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (mandatory, especially RULE 2: tenant isolation, RULE 4: schemas first)
> 2. `docs/architecture/02-database-schema.md` — CreditTransaction model, User.credits_balance field
> 3. `docs/architecture/03-api-contract.md` — `GET /v1/credits/balance` spec
> 4. `docs/architecture/05-security-privacy.md` — Stripe webhook validation pattern
> 5. `docs/design/CLAUDE_FRONTEND.md` — frontend rules for credits balance display

---

## User Story
As a user, I want my credit balance to correctly reflect my usage so I understand my consumption and can top up when needed.

## Acceptance Criteria
- [ ] AC-1: `CreditTransaction` records created for each operation using costs from `prd/05-monetization.md`: ingestion (1/page), meta_doc_haiku (18 credits), meta_doc_sonnet (45 credits), chat_haiku (3 credits), chat_sonnet (8 credits), nl_graph_query (2 credits)
- [ ] AC-2: `User.credits_balance` updated atomically with transaction (no race conditions)
- [ ] AC-3: Credit balance shown in sidebar footer
- [ ] AC-4: Before Meta-Doc generation: check `credits_balance >= estimated_credits`; if not, return `402` before starting job
- [ ] AC-5: `GET /v1/credits/balance` returns current balance + recent transactions
- [ ] AC-6: Stripe webhook: `checkout.session.completed` for credit top-up adds credits to balance
- [ ] AC-7: Free tier signup: 500 credits added via `signup_bonus` transaction (see `prd/05-monetization.md`)

## Technical Notes

### Files to Create
- `src/services/credit_service.py` — `deduct()`, `check_balance()`, `add_credits()`
- `src/api/routes/credits.py` — `GET /v1/credits/balance`

### Files to Modify
- `src/workers/metadoc_tasks.py` — call `credit_service.deduct()` after generation
- `src/workers/ingestion_tasks.py` — call `credit_service.deduct(1_per_page)` after embedding
- `src/api/routes/metadoc.py` — call `check_balance()` before enqueueing
- `src/api/routes/webhooks.py` — handle `checkout.session.completed` Stripe event

### Credit Costs Reference
| Operation | Credits | Source of truth |
|---|---|---|
| Ingestion | 1 per page | — |
| Meta-Doc (Claude Haiku) | **18** | `prd/05-monetization.md` |
| Meta-Doc (Claude Sonnet) | **45** | `prd/05-monetization.md` |
| Chat (Claude Haiku) | **3** | `prd/05-monetization.md` |
| Chat (Claude Sonnet) | **8** | `prd/05-monetization.md` |
| NL Graph Query | **2** | `prd/05-monetization.md` |
| Signup bonus (free tier) | +500 | — |
| Referral signup bonus | +200 | `prd/05-monetization.md` |
| Referral reward (first upload) | +200 | `prd/05-monetization.md` |

### Atomic Deduction (prevent race conditions)
```python
# src/services/credit_service.py
from sqlmodel import select
from sqlalchemy import update

class CreditService(BaseService):
    async def deduct(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        operation: str,
    ) -> CreditTransaction:
        # SELECT FOR UPDATE prevents concurrent race conditions
        user = (
            await db.exec(
                select(User).where(User.id == user_id).with_for_update()
            )
        ).one()

        if user.credits_balance < amount:
            raise HTTPException(
                status_code=402,
                detail={"code": "INSUFFICIENT_CREDITS", "message": f"Need {amount}, have {user.credits_balance}"},
            )

        user.credits_balance -= amount
        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            operation=operation,
            balance_after=user.credits_balance,
        )
        db.add(transaction)
        await db.commit()
        return transaction

    async def add_credits(
        self,
        db: AsyncSession,
        user_id: str,
        amount: int,
        operation: str,
    ) -> CreditTransaction:
        user = (
            await db.exec(
                select(User).where(User.id == user_id).with_for_update()
            )
        ).one()
        user.credits_balance += amount
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            operation=operation,
            balance_after=user.credits_balance,
        )
        db.add(transaction)
        await db.commit()
        return transaction
```

### Stripe Webhook Validation Pattern
```python
# src/api/routes/webhooks.py
import stripe
from fastapi import Request, HTTPException

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"]["user_id"]
        credits = int(session["metadata"]["credits"])
        await credit_service.add_credits(db, user_id, credits, operation="stripe_topup")

    return {"received": True}
```

### Frontend: Credits Balance in Sidebar
```typescript
// Fetch balance and show in sidebar footer
const { data } = useSWR("/v1/credits/balance", apiFetch);
// Display: "{data?.balance} credits remaining"
```

## Definition of Done
- [ ] Credits deducted correctly for all operations (ingestion, haiku, sonnet)
- [ ] Pre-generation 402 returned when insufficient credits
- [ ] No race conditions: 10 concurrent deductions tested with SELECT FOR UPDATE
- [ ] Stripe webhook creates credit transaction on checkout.session.completed
- [ ] Free signup adds 500 credits via signup_bonus transaction
- [ ] `make quality` + `make test` pass

## Testing This Story

```bash
# Integration tests:
uv run pytest tests/integration/api/test_credits.py -v

# Manual credit deduction test:
TOKEN="your_clerk_token"
curl http://localhost:8000/v1/credits/balance \
  -H "Authorization: Bearer ${TOKEN}"
# Expected: {"balance": 500, "transactions": [...]}

# Test insufficient credits:
# Drain credits to 0, then call POST /v1/metadoc/generate
# Expected: 402 {"detail": {"code": "INSUFFICIENT_CREDITS", "message": "Need 18, have 0"}}

# Test Stripe webhook (use Stripe CLI):
stripe listen --forward-to http://localhost:8000/webhooks/stripe
stripe trigger checkout.session.completed
# Expected: credit transaction created, user balance updated

# Race condition test:
uv run pytest tests/integration/api/test_credits.py::test_concurrent_deductions -v

# Quality:
make quality
```

**Passing result:** Credits deducted correctly. 402 before generation when insufficient. Stripe webhook adds credits. No race conditions.

---

## Agent Implementation Brief

```
Implement STORY-023: Credits System.

Read first:
1. CLAUDE.md (architecture rules — RULE 2: tenant isolation, RULE 4: schemas first)
2. docs/architecture/02-database-schema.md (CreditTransaction model, User.credits_balance)
3. docs/architecture/03-api-contract.md (GET /v1/credits/balance spec)
4. docs/architecture/05-security-privacy.md (Stripe webhook validation pattern)
5. docs/stories/EPIC-08-polish/STORY-023.md (this file)

Key constraints:
- Use SELECT FOR UPDATE for all deductions (prevents race conditions)
- Deduct AFTER generation success (never before)
- 402 check happens in the route handler BEFORE enqueueing ARQ job
- Stripe webhook validates signature via stripe.Webhook.construct_event()
- signup_bonus: 500 credits added when user first completes onboarding (STORY-019)
- CreditTransaction records every change (positive and negative)

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
git add -A && git commit -m "feat(ravenbase): STORY-023 [description]"
git push

# 3. Regenerate client (if this story added/changed API endpoints):
cd ../ravenbase-web && npm run generate-client
git add src/lib/api-client/ && git commit -m "chore: regenerate client after STORY-023"
git push && cd ../ravenbase-api

# 4. Mark complete:
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-023
git add docs/stories/epics.md && git commit -m "docs: mark STORY-023 complete"
```
