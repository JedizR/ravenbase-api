# STORY-034: Referral System

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-019 (onboarding), STORY-023 (credits system must be complete)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — referral system story.

## Component
UI/Polish

---

> **Before You Start — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (3-layer, lazy imports, structlog)
> 2. `docs/prd/05-monetization.md` — referral rules (rewards, caps, code format)
> 3. `docs/architecture/02-database-schema.md` — referral_code, referred_by_user_id, ReferralTransaction
> 4. `docs/stories/EPIC-08-polish/STORY-023.md` — credit transaction patterns

---

## User Story
As a satisfied user, I want a referral link I can share to earn credits when friends actually use the product.
As a new user arriving via referral, I want bonus credits so I can experience more before deciding to pay.

## Context
- Referral code = first 8 chars of user UUID, uppercase (e.g. `550E8400`)
- **Referee** gets +200 bonus credits on signup → 700 total (500 base + 200 referral)
- **Referrer** gets +200 credits when referee completes **first file upload** (not signup)
- Activation trigger prevents fake account abuse and ensures referrer earns via genuine users
- Monthly cap: 50 rewards per referrer (anti-abuse; invisible to normal users)
- Model switching for referral credits: still Haiku only (Free tier rules apply)

## Acceptance Criteria
- [ ] AC-1: On `user.created` Clerk webhook, `User.referral_code` auto-generated as first 8 chars of `User.id`, uppercase
- [ ] AC-2: If `/register?ref=CODE` was captured in frontend `localStorage` before Clerk redirect, backend `POST /v1/account/apply-referral` sets `User.referred_by_user_id` after signup. Invalid/expired codes silently ignored (not an error to the user).
- [ ] AC-3: Signup with valid referral code: referee receives +200 `signup_referral_bonus` credit transaction immediately. Referrer is NOT yet credited.
- [ ] AC-4: When referred user creates their first `Source` record (file or text): award referrer +200 credits via `referral_reward` transaction IF `User.referral_reward_claimed = False`
- [ ] AC-5: `User.referral_reward_claimed = True` set after AC-4 fires — one-time only
- [ ] AC-6: `ReferralTransaction` record created for every reward event
- [ ] AC-7: Monthly cap: if referrer already has 50 `ReferralTransaction` records this calendar month, skip and log `referral.monthly_cap_reached`
- [ ] AC-8: `GET /v1/account/referral` returns code, URL, stats
- [ ] AC-9: Settings → Referrals page shows referral link with one-click copy button, basic stats (total referrals, pending, credits earned)
- [ ] AC-10: Referral code lookup is case-insensitive (normalize input to uppercase before DB lookup)

## Technical Notes

### Files to Create
- `src/services/referral_service.py`

### Files to Modify
- `src/api/routes/webhooks.py` — call `generate_referral_code()` in `user.created` handler
- `src/workers/tasks/ingestion.py` — call `award_referrer_on_first_upload()` after first Source
- `src/api/routes/account.py` — add `GET /v1/account/referral` + `POST /v1/account/apply-referral`

### Referral Service Pattern

```python
# src/services/referral_service.py

def generate_referral_code(user_id: uuid.UUID) -> str:
    return str(user_id).replace("-", "").upper()[:8]

async def award_referrer_on_first_upload(referee_id: uuid.UUID, db: AsyncSession) -> None:
    """Triggered from ingestion task on first Source creation for a user."""
    referee = await db.get(User, referee_id)
    if not referee or not referee.referred_by_user_id or referee.referral_reward_claimed:
        return

    referrer = await db.get(User, referee.referred_by_user_id)
    if not referrer or not referrer.is_active:
        return

    # Monthly cap check
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly = (await db.execute(
        select(func.count()).where(
            ReferralTransaction.referrer_user_id == referrer.id,
            ReferralTransaction.created_at >= month_start,
        )
    )).scalar()
    if monthly >= 50:
        log.warning("referral.monthly_cap_reached", referrer_id=str(referrer.id))
        return

    referrer.credits_balance += 200
    referee.referral_reward_claimed = True
    db.add(ReferralTransaction(
        referrer_user_id=referrer.id,
        referee_user_id=referee.id,
        referrer_credits_awarded=200,
        referee_credits_awarded=0,
        trigger_event="first_upload",
    ))
    await db.commit()
    log.info("referral.reward_awarded", referrer=str(referrer.id), referee=str(referee.id))
```

### Architecture Constraints
- `referral_reward_claimed` is the idempotency guard — once True, never reward again
- Referral code generation is server-side (Clerk webhook) — never from registration form
- Frontend captures `?ref=CODE` in localStorage before Clerk redirect, calls `apply-referral` post-signup

## Definition of Done
- [ ] Referral codes auto-generated on user creation
- [ ] Referee bonus (+200) at signup; referrer reward (+200) on first upload
- [ ] Monthly cap enforced; `referral_reward_claimed` prevents double-award
- [ ] `GET /v1/account/referral` returns correct stats
- [ ] Settings → Referrals page with copy button
- [ ] `make quality && make test` passes

## Testing This Story

```bash
# Test referral flow end-to-end:
# 1. Create user A (referral_code auto-assigned on signup via Clerk webhook)
# 2. Create user B via POST /v1/account/apply-referral body: {"referral_code": "USER_A_CODE"}
# 3. GET /v1/credits/balance for user B → expect 700 (500 base + 200 referral bonus)
# 4. GET /v1/credits/balance for user A → expect 500 (referrer reward NOT yet triggered)
# 5. User B creates first Source (POST /v1/ingest/upload or /v1/ingest/text)
# 6. GET /v1/credits/balance for user A → expect 700 (+200 referral reward triggered)
# 7. User B uploads a second file
# 8. GET /v1/credits/balance for user A → still 700 (referral_reward_claimed prevents double)
# 9. GET /v1/account/referral for user A → total_referrals: 1, credits_earned: 200
# 10. Test monthly cap: seed 50 ReferralTransaction rows for user A this calendar month,
#     trigger a 51st referral activation → verify reward NOT granted, warning logged
# 11. Test invalid code: POST /v1/account/apply-referral body: {"referral_code": "INVALID1"}
#     → expect 200 OK (silently ignored — invalid codes are not errors)
```

## Agent Implementation Brief

```
Implement STORY-034: Referral System.

Read first:
1. CLAUDE.md
2. docs/prd/05-monetization.md (referral rules, reward amounts, caps)
3. docs/architecture/02-database-schema.md (referral_code, ReferralTransaction)
4. docs/stories/EPIC-08-polish/STORY-023.md (credit transaction patterns)
5. docs/stories/EPIC-08-polish/STORY-034.md (this file)

Key constraints:
- Referrer reward triggers on FIRST UPLOAD, not signup — use referral_reward_claimed
- Monthly cap 50 rewards/referrer
- Never award if either account is inactive
Show plan first.
```

## Development Loop
Follow `docs/DEVELOPMENT_LOOP.md`.
```bash
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-034 referral system"
```
