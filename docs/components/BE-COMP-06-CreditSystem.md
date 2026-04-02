# CreditSystem

> **Component ID:** BE-COMP-06
> **Epic:** EPIC-08 — Polish & Production Hardening
> **Stories:** STORY-023
> **Type:** Backend (with frontend balance display)

---

## Purpose

The CreditSystem is the financial gate for all AI operations in Ravenbase. It enforces per-operation credit deduction with a ledger for auditability, prevents race conditions using `SELECT FOR UPDATE`, and integrates Stripe webhooks for credit top-ups. Every component that calls an LLM routes through `CreditService.check_or_raise()` (before the operation) and `CreditService.deduct()` (after success). The frontend sidebar displays the live balance.

---

## User Journey

Credits flow automatically — users rarely interact with them directly:

1. New user registers → Clerk webhook fires → backend creates User + 500 credits (`signup_bonus` transaction)
2. User performs a paid operation (e.g., generate Meta-Doc):
   a. API calls `CreditService.check_or_raise(user_id, 18)` — raises `402` if balance < 18
   b. Operation runs (LLM streams tokens)
   c. On success: `CreditService.deduct(user_id, 18, "meta_doc_haiku")` — atomic deduction
   d. Sidebar balance updates on next `GET /v1/credits/balance` poll
3. User buys credit top-up via Stripe:
   a. Stripe `checkout.session.completed` webhook fires
   b. `CreditService.add_credits(user_id, amount, "stripe_topup")` runs
   c. Sidebar balance increments
4. Credits reach 0 → next paid operation returns `402 INSUFFICIENT_CREDITS`
5. Sidebar shows `⚠ LOW CREDITS` warning when balance < 50

**Admin users:** `CreditService.check_or_raise()` and `CreditService.deduct()` return early — no credits consumed. Sidebar shows `◆ ADMIN_ACCESS` instead of balance.

---

## Admin Bypass

**CRITICAL — BUG-006: Admin bypass NOT YET IMPLEMENTED**

The `CreditService` currently has no admin bypass. Admin users consume real credits during testing, which blocks end-to-end testing of all LLM features.

**Required implementation in `src/services/credit_service.py`:**

```python
async def check_or_raise(self, db: AsyncSession, user_id: str, amount: int) -> None:
    admin_ids = {u.strip() for u in settings.ADMIN_USER_IDS.split(",") if u.strip()}
    if user_id in admin_ids:
        log.info("credit.admin_bypass.check", user_id=user_id, amount=amount)
        return  # Admin users never blocked
    # ... existing implementation ...

async def deduct(self, db, user_id: str, amount: int, operation: str, reference_id=None):
    admin_ids = {u.strip() for u in settings.ADMIN_USER_IDS.split(",") if u.strip()}
    if user_id in admin_ids:
        log.info("credit.admin_bypass.deduct", user_id=user_id, operation=operation)
        return CreditTransaction(
            user_id=uuid.UUID(user_id),
            amount=0,
            balance_after=-1,  # -1 sentinel = admin bypass
            operation=f"admin_bypass:{operation}",
        )
    # ... existing implementation ...
```

**Frontend admin indicator** (Sidebar.tsx):
```tsx
{user?.is_admin ? (
  <p className="font-mono text-xs text-muted-foreground">◆ ADMIN_ACCESS</p>
) : (
  <p className="font-mono text-xs">{creditsBalance} credits remaining</p>
)}
```

`GET /v1/me` must return `{is_admin: boolean}` for the frontend to detect admin users.

**Verification after fix:**
- Set `ADMIN_USER_IDS=your_clerk_user_id` in `.envs/.env.dev`
- Generate a Meta-Doc → credit balance in DB unchanged
- `credit_transactions` table → row with `operation="admin_bypass:meta_doc_haiku"`

---

## Known Bugs / Current State

**BUG-006 (HIGH — blocks all testing):** No admin credit bypass.
- **Root cause:** `src/services/credit_service.py` has no `ADMIN_USER_IDS` check in `check_or_raise()` or `deduct()`. Admin users get 402 errors after their initial 500 credits are spent, blocking all LLM feature testing.
- **Fix:** Add admin bypass as shown in Admin Bypass section above.
- **Story:** STORY-040

**BUG-011 (HIGH):** `ADMIN_USER_IDS` is a placeholder in both repos.
- **Root cause:** `ravenbase-web/.env.local` has `ADMIN_USER_IDS=placeholder` and `ravenbase-api/.envs/.env.dev` similarly. No real Clerk user ID is set.
- **Fix:** User must retrieve their Clerk user ID from Clerk Dashboard → Users → click account → copy `user_xxx` ID. Set in BOTH repos' env files.
- **Story:** STORY-040

---

## Acceptance Criteria

- [ ] `CreditService.check_or_raise()` raises 402 before any paid operation
- [ ] `CreditService.deduct()` uses `SELECT FOR UPDATE` — concurrent deductions never double-spend
- [ ] `CreditTransaction` record created for every credit change (deduction, addition, bypass)
- [ ] Admin users: `check_or_raise()` returns early, `deduct()` returns zero-amount transaction
- [ ] `GET /v1/credits/balance` returns `{balance, transactions: [...]}` (last 20)
- [ ] Stripe `checkout.session.completed` webhook adds credits
- [ ] Free signup bonus: 500 credits via `signup_bonus` transaction
- [ ] Referral bonuses: +200 on signup via referral, +200 to referrer on first upload
- [ ] Concurrent deduction test: 10 simultaneous → exact expected balance
- [ ] Frontend sidebar shows `◆ ADMIN_ACCESS` for admin users

---

## Cross-references

- `docs/design/AGENT_DESIGN_PREAMBLE.md` — MANDATORY read before any JSX
- `BE-COMP-01-IngestionPipeline.md` — ingestion credits (1/page)
- `BE-COMP-02-GraphEngine.md` — NL graph query credits (2)
- `BE-COMP-04-GenerationEngine.md` — Meta-Doc (18/45) and Chat (3/8) credits
- `docs/architecture/03-api-contract.md` — `/v1/credits/balance` endpoint
- `docs/components/REFACTOR_PLAN.md` — BUG-006, BUG-011, ADMIN-001 fix details

---

## Goal

The CreditSystem owns per-operation credit deduction with ledger tracking. It ensures atomic credit balance updates (no race conditions), provides a balance inquiry endpoint, integrates with Stripe webhooks for top-ups, and enforces pre-operation credit checks. Every LLM and storage operation in the system flows through this component.

---

## Product Requirements

1. **Credit Transaction Ledger:** Every credit change (deduction or addition) creates a `CreditTransaction` record: `user_id`, `amount` (positive or negative), `operation`, `balance_after`, `created_at`.

2. **Atomic Deduction:** `CreditService.deduct()` uses `SELECT FOR UPDATE` to prevent race conditions when concurrent operations deduct credits simultaneously.

3. **Credit Costs (per `prd/05-monetization.md`):**
   - Ingestion: 1 credit per page
   - Meta-Doc (Claude Haiku): 18 credits
   - Meta-Doc (Claude Sonnet): 45 credits
   - Chat (Claude Haiku): 3 credits
   - Chat (Claude Sonnet): 8 credits
   - NL Graph Query: 2 credits
   - Free signup bonus: +500 credits
   - Referral signup bonus: +200 credits
   - Referral reward (first upload): +200 credits

4. **Balance Check Before Operation:** Before any paid operation (Meta-Doc, Chat, NL query), the system checks `user.credits_balance >= estimated_credits` and returns `402 INSUFFICIENT_CREDITS` if insufficient — BEFORE any LLM call or job enqueue.

5. **Deduct After Success:** Credits are deducted AFTER successful operation completion, not before. If an operation fails, no deduction occurs.

6. **Balance Endpoint:** `GET /v1/credits/balance` returns `{balance, transactions: [...]}` with recent transactions.

7. **Stripe Top-Up:** `POST /webhooks/stripe` handles `checkout.session.completed` to add credits from purchased top-up packs.

8. **Sidebar Display:** Frontend shows credit balance in sidebar footer.

---

## Criteria and Tests

| Criterion | Test |
|---|---|
| Credits deducted for all operations | Complete operation → SELECT * FROM credit_transactions WHERE user_id = X |
| Race condition: concurrent deductions | 10 simultaneous requests → balance = initial - (10 × cost) |
| Pre-operation 402 check | Set balance to 0 → call generate → 402 before any work |
| Deduct after success | Complete generation → check balance decreased |
| Stripe webhook adds credits | Trigger checkout.session.completed → balance increased |
| Free signup +500 bonus | New user created → credit_transaction with operation=signup_bonus |
| Referral signup +200 | Referral code used on signup → +200 credits |
| Referral first upload +200 | Referee uploads first file → referrer gets +200 |
| Balance endpoint returns transactions | GET /v1/credits/balance → includes recent transactions |

---

## Related Stories

| Story | Title | Type | Description |
|---|---|---|---|
| [STORY-023](../stories/EPIC-08-polish/STORY-023.md) | Credits System | Backend | Deduct, ledger, 402 check, Stripe webhook |

---

## Subcomponents

The CreditSystem has 1 subcomponent covering the full credit lifecycle.

---

### SUBCOMP-06A: Credit Lifecycle

**Stories:** STORY-023
**Files:** `src/services/credit_service.py`, `src/api/routes/credits.py`, `src/api/routes/webhooks.py`, `src/models/credit_transaction.py`, `alembic/versions/XXX_add_credit_transactions.py`, `tests/integration/api/test_credits.py`

#### Details
The CreditService manages the complete credit lifecycle: atomic deductions with `SELECT FOR UPDATE` locking, balance checks before paid operations, the `CreditTransaction` ledger, and the Stripe webhook handler for top-ups. Every component that calls an LLM or storage API integrates with this service.

#### Criteria of Done
- [ ] `CreditTransaction` model: `user_id`, `amount`, `operation`, `balance_after`, `created_at`
- [ ] `deduct(db, user_id, amount, operation)` uses `SELECT FOR UPDATE` — no race conditions
- [ ] `check_or_raise(db, user_id, amount)` raises 402 if insufficient — called BEFORE operation
- [ ] `add_credits(db, user_id, amount, operation)` for top-ups and bonuses
- [ ] All 8 credit costs correctly defined as constants
- [ ] `GET /v1/credits/balance` returns `{balance, transactions: [...]}` (last 20)
- [ ] Stripe `checkout.session.completed` webhook adds credits with correct metadata
- [ ] Free signup: 500 credits via `signup_bonus` transaction
- [ ] Referral bonuses: +200 on signup via referral, +200 to referrer on first upload
- [ ] Concurrent deduction test: 10 simultaneous → exact expected balance

#### Checklist
- [ ] `SELECT FOR UPDATE` on `User` row before decrementing balance
- [ ] `CreditTransaction` record created in same transaction as balance update
- [ ] `balance_after` field records balance immediately after this transaction
- [ ] 402 raised BEFORE any expensive operation (LLM call, job enqueue)
- [ ] `deduct()` called AFTER generation/chat success (not before)
- [ ] Stripe webhook: `checkout.session.completed` reads `metadata.user_id` and `metadata.credits`
- [ ] Stripe signature validated: `stripe.Webhook.construct_event()`
- [ ] Credit cost constants: `INGESTION_PER_PAGE = 1`, `META_DOC_HAIKU = 18`, etc.
- [ ] Alembic migration for `credit_transactions` table
- [ ] Integration test for concurrent deductions

#### Testing
```bash
# Balance endpoint:
curl http://localhost:8000/v1/credits/balance \
  -H "Authorization: Bearer TOKEN"
# Expected: {"balance": 500, "transactions": [{"operation": "signup_bonus", "amount": 500, ...}]}

# 402 insufficient credits:
# Set user balance to 0 via psql: UPDATE users SET credits_balance = 0 WHERE id = 'user_id'
curl -X POST http://localhost:8000/v1/metadoc/generate \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "model": "haiku"}'
# Expected: 402 {"detail": {"code": "INSUFFICIENT_CREDITS"}}

# Concurrent deductions:
uv run pytest tests/integration/api/test_credits.py::test_concurrent_deductions -v
# Expected: exact balance after 10 concurrent deductions

# Stripe webhook (use Stripe CLI):
stripe listen --forward-to http://localhost:8000/webhooks/stripe
stripe trigger checkout.session.completed
# Check: psql -c "SELECT * FROM credit_transactions WHERE operation = 'stripe_topup'"

make quality
```
