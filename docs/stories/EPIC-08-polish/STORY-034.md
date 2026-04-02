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

## UX & Visual Quality Requirements

### Settings → Referrals Page UX
1. Referral link display card:
   bg-card rounded-2xl border border-border p-6 space-y-4

2. Referral link input (read-only):
   - Shows: https://ravenbase.app/register?ref=XXXXXX
   - Input: bg-secondary rounded-xl px-4 py-3 font-mono text-sm
   - Read-only, not editable
   - Full width on mobile

3. Copy button animation:
   - Default: "◆ COPY_LINK" with Copy icon
   - On click: call navigator.clipboard.writeText(referralUrl)
   - Success state (2 seconds): "◆ COPIED!" with Check icon
     (green check icon, text-success)
   - Button: rounded-full border border-border bg-card hover:bg-secondary
   - Transition: all 150ms ease on text/icon swap
   - TIMING: exactly 2000ms (2 seconds) before returning to default state

4. Social share buttons:
   - Twitter/X: opens https://twitter.com/intent/tweet?text=...
   - LinkedIn: opens https://www.linkedin.com/sharing/share-offsite/?url=...
   - Each button: rounded-full border border-border p-2 hover:bg-secondary
   - Open in new tab: target="_blank" rel="noopener noreferrer"

5. Referral stats card:
   bg-card rounded-2xl border border-border p-6
   Show:
   - "X users referred" — large font-mono number in forest green
   - "X credits earned" — secondary stat
   - Progress bar toward next reward:
     "X more referrals to unlock Pro month free"
     Progress bar: bg-primary [&>div]:bg-warning (amber progress on green bar)

6. Reward milestones list:
   Visual timeline of reward tiers:
   1 referral → 100 bonus credits
   3 referrals → 500 bonus credits
   5 referrals → 1 month Pro free
   Each milestone: checkmark (green if reached), dot (amber if next), circle (gray if future)

## Definition of Done
- [ ] Referral codes auto-generated on user creation
- [ ] Referee bonus (+200) at signup; referrer reward (+200) on first upload
- [ ] Monthly cap enforced; `referral_reward_claimed` prevents double-award
- [ ] `GET /v1/account/referral` returns correct stats
- [ ] Settings → Referrals page with copy button
- [ ] `make quality && make test` passes

## Final Localhost Verification (mandatory before marking complete)

After `make quality && make test` passes, verify the running application works:

**Step 1 — Start dev server:**
```bash
cd ravenbase-api && make run
```

**Step 2 — Verify no runtime errors:**
- Test the referral endpoints with curl or a tool like Postman
- Confirm no unhandled exceptions in server logs
- Confirm structlog output is clean

**Step 3 — Report one of:**
- ✅ `localhost verified` — referral system runs correctly
- ⚠️ `Issue found: [describe issue]` — fix before committing docs

Only commit the docs update (epics.md, story-counter, project-status, journal) AFTER localhost verification passes.

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

## Frontend Agent Brief

> **Skill Invocations — invoke each skill before the corresponding phase:**
>
> **Phase 1 (Read/Design):** `Use /frontend-design — enforce production-grade aesthetic compliance`
> **Phase 2 (Components):** `Use /tailwindcss — for Tailwind CSS v4 token system`
> **Phase 3 (API/TanStack):** `Use /tailwindcss-animations — for micro-interaction patterns`
> **Phase 4 (Verification):** `Use /superpowers:verification-before-completion — before claiming done`

---

```
🎯 Target: Claude Code / MiniMax-M2.7 — Ultra-detailed planning and implementation
💡 Optimization: MiniMax-M2.7 directive — WRITE EVERYTHING IN MAXIMUM DETAIL.
   Plans MUST be 1500-3000 lines. Never short-circuit with "see code below".
   Write complete explanations, complete code, complete verification commands.

═══════════════════════════════════════════════════════════════════
STEP 0 — PROJECT CONTEXT (carry forward to every phase)
═══════════════════════════════════════════════════════════════════

Ravenbase Frontend: Next.js 15 App Router + Tailwind CSS v4 + shadcn/ui + TanStack Query
Design system: CSS variables only (no hardcoded hex). Dark mode via .dark class on <html>
Brand colors: Primary=#2d4a3e (forest green), Background=#f5f3ee (warm cream), Accent=#a8c4b2
DO NOT introduce new design aesthetics — follow the established brand system exactly.
Page directory: app/(dashboard)/settings/referrals/page.tsx (already exists)
Page loading: app/(dashboard)/settings/referrals/loading.tsx (already exists)
API endpoint: GET /v1/account/referral (frontend must call this)
Backend must be complete first: run grep -n "referral" ravenbase-api/src/api/routes/account.py

═══════════════════════════════════════════════════════════════════
STEP 1 — READ PHASE (mandatory — read ALL files before touching code)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /frontend-design

Read ALL files in order — NOT in parallel — every file completely:

1. CLAUDE.md
   → All 19 rules. Critical rules for this story:
     RULE 6 (TanStack Query for server state — NEVER useState+useEffect for API data)
     RULE 2 (no <form> tags — use onClick)
     RULE 7 (shadcn/ui components)
     RULE 9 (use RavenbaseLogo/RavenbaseLockup — never placeholder div)

2. docs/design/AGENT_DESIGN_PREAMBLE.md
   → Anti-patterns to reject on sight:
     ❌ className="rounded-lg" on cards → must be rounded-2xl
     ❌ className="rounded-md" on CTAs → must be rounded-full
     ❌ bg-[#2d4a3e] → must be bg-primary
     ❌ bg-[#f5f3ee] → must be bg-background
     ❌ bg-[#ffc00d] → must be bg-warning
     ❌ floating labels → labels always ABOVE input
     ❌ className="dark" or "light" on route group layouts

3. docs/design/00-brand-identity.md
   → Mono label pattern: ◆ REFERRAL_LINK, ◆ REFERRAL_STATS, ◆ MILESTONES
   → Brand voice rules
   → Logo usage: RavenbaseLogo and RavenbaseLockup from @/components/brand

4. docs/design/01-design-system.md
   → All CSS variable definitions (light and dark)
   → Card style: bg-card rounded-2xl border border-border
   → CTA: rounded-full bg-primary text-primary-foreground
   → Section mono label: text-xs font-mono text-muted-foreground tracking-wider
   → Success color: text-success (#3d8b5a)
   → Warning color: bg-warning (#ffc00d)

5. docs/design/04-ux-patterns.md
   → Copy button: 2-second success state (EXACTLY 2000ms)
   → Social share: Twitter intent URL, LinkedIn share-offsite URL
   → Progress bar: bg-primary fill, bg-secondary track
   → Milestone indicators: CheckCircle2 (reached), amber dot (next), gray circle (future)
   → Section 10: use-copy-to-clipboard.ts hook pattern

6. docs/stories/EPIC-08-polish/STORY-034.md (this file)
   → All ACs. Focus: AC-9 (frontend), AC-1 through AC-8 (backend)
   → CONFIRMED: Read every acceptance criterion

═══════════════════════════════════════════════════════════════════
STEP 2 — BACKEND AVAILABILITY CHECK
═══════════════════════════════════════════════════════════════════

Before writing frontend code, verify the backend API exists:

grep -n "referral" /Users/admin/destination/ravenbase/ravenbase-api/src/api/routes/account.py | head -20

Expected output should include:
- GET /v1/account/referral
- POST /v1/account/apply-referral

If these endpoints do NOT exist → this frontend story cannot be fully tested.
Document the dependency block and proceed with UI implementation only.

═══════════════════════════════════════════════════════════════════
STEP 3 — PAGE DESIGN (Phase 2a — full code for page.tsx)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss

FILE: app/(dashboard)/settings/referrals/page.tsx

This file ALREADY EXISTS. You are enhancing it to match this exact specification.

Complete code — every line, no omissions:

```tsx
"use client"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { Copy, Check, Linkedin } from "lucide-react"
import { CheckCircle2 } from "lucide-react"
import { useApiFetch } from "@/lib/api-client"

interface ReferralResponse {
  referral_code: string
  referral_url: string
  total_referrals: number
  pending_referrals: number
  credits_earned: number
  current_month_count: number
  monthly_cap: number
}

export default function ReferralsPage() {
  const [copied, setCopied] = useState(false)
  const apiFetch = useApiFetch()

  // TanStack Query for referral data — RULE 6: useQuery for server state
  const { data, isLoading } = useQuery<ReferralResponse>({
    queryKey: ["referral"],
    queryFn: () => apiFetch<ReferralResponse>("/v1/account/referral"),
    staleTime: 30_000,  // Referral stats change infrequently
  })

  const referralUrl = data?.referral_url ?? ""
  const totalReferrals = data?.total_referrals ?? 0
  const creditsEarned = data?.credits_earned ?? 0

  // COPY BUTTON STATE MACHINE:
  // State: COPY_LINK (default) → COPIED! (2 seconds) → COPY_LINK
  // AC-9b: Exactly 2000ms timeout before returning to default
  const handleCopy = async () => {
    await navigator.clipboard.writeText(referralUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Milestone configuration
  const milestones = [
    { count: 1, reward: "100 bonus credits", reached: totalReferrals >= 1 },
    { count: 3, reward: "500 bonus credits", reached: totalReferrals >= 3 },
    { count: 5, reward: "1 month Pro free", reached: totalReferrals >= 5 },
  ]
  const nextMilestone = milestones.find((m) => !m.reached)
  const progressPercent = nextMilestone
    ? (totalReferrals / nextMilestone.count) * 100
    : 100

  return (
    <div className="space-y-8">
      {/* Referral link card */}
      <div className="bg-card rounded-2xl border border-border p-6 space-y-4">
        <p className="text-xs font-mono text-muted-foreground tracking-wider">
          ◆ REFERRAL_LINK
        </p>

        {/* Read-only URL input with copy button overlay */}
        <div className="relative">
          <input
            readOnly
            value={referralUrl}
            aria-label="Your referral link"
            className="w-full bg-secondary rounded-xl px-4 py-3 pr-20
                       font-mono text-sm text-foreground
                       border border-border outline-none"
          />
          {/* Copy button — overlays right side of input */}
          <button
            onClick={handleCopy}
            aria-label={copied ? "Link copied to clipboard" : "Copy referral link to clipboard"}
            className="absolute right-2 top-1/2 -translate-y-1/2
                       flex items-center gap-1.5 px-3 py-1.5 rounded-full
                       border border-border bg-card hover:bg-secondary
                       text-xs font-mono transition-all duration-150
                       min-h-[36px]"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-success" />
                <span className="text-success">COPIED!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 text-muted-foreground" />
                <span className="text-muted-foreground">COPY_LINK</span>
              </>
            )}
          </button>
        </div>

        {/* Social share buttons */}
        <div className="flex gap-2">
          {/* Twitter/X share */}
          <a
            href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(
              "I'm using Ravenbase to build my AI memory. Get 200 free credits: " + referralUrl
            )}`}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Share on Twitter"
            className="p-2 rounded-full border border-border hover:bg-secondary
                       transition-colors"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.746l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
          </a>
          {/* LinkedIn share */}
          <a
            href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(referralUrl)}`}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Share on LinkedIn"
            className="p-2 rounded-full border border-border hover:bg-secondary
                       transition-colors"
          >
            <Linkedin className="w-4 h-4" />
          </a>
        </div>
      </div>

      {/* Stats card */}
      <div className="bg-card rounded-2xl border border-border p-6 space-y-4">
        <p className="text-xs font-mono text-muted-foreground tracking-wider">
          ◆ REFERRAL_STATS
        </p>

        <div className="flex items-baseline gap-2">
          <span className="font-mono text-4xl font-bold text-primary">
            {isLoading ? "—" : totalReferrals}
          </span>
          <span className="text-sm text-muted-foreground">users referred</span>
        </div>

        <div className="text-sm text-muted-foreground">
          <span className="font-mono text-foreground">
            {isLoading ? "—" : creditsEarned}
          </span>{" "}
          credits earned
        </div>

        {/* Progress bar toward next reward milestone */}
        {nextMilestone && (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">
              {nextMilestone.count - totalReferrals} more referral
              {nextMilestone.count - totalReferrals !== 1 ? "s" : ""} to unlock{" "}
              {nextMilestone.reward}
            </p>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-300"
                style={{ width: `${Math.min(100, progressPercent)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Milestone timeline */}
      <div className="bg-card rounded-2xl border border-border p-6 space-y-3">
        <p className="text-xs font-mono text-muted-foreground tracking-wider">
          ◆ MILESTONES
        </p>
        {milestones.map((m, i) => {
          const isNext =
            !m.reached && milestones.slice(0, i).every((x) => x.reached)
          return (
            <div key={i} className="flex items-center gap-3">
              {m.reached ? (
                // Green checkmark: milestone reached
                <CheckCircle2 className="w-5 h-5 text-success shrink-0" />
              ) : isNext ? (
                // Amber dot: next milestone to reach
                <div className="w-5 h-5 rounded-full bg-warning shrink-0" />
              ) : (
                // Gray circle: future milestone
                <div className="w-5 h-5 rounded-full bg-secondary border border-border shrink-0" />
              )}
              <span
                className={`text-sm ${
                  m.reached ? "text-foreground" : "text-muted-foreground"
                }`}
              >
                {m.count} referral{m.count > 1 ? "s" : ""} → {m.reward}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

═══════════════════════════════════════════════════════════════════
STEP 4 — LOADING STATE (Phase 2b — required by RULE 10)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss

FILE: app/(dashboard)/settings/referrals/loading.tsx

This file ALREADY EXISTS. Verify it matches this exact specification.

```tsx
import { Skeleton } from "@/components/ui/skeleton"

export default function ReferralsLoading() {
  return (
    <div className="space-y-8">
      {/* Skeleton for ◆ REFERRAL_LINK card */}
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-40 w-full rounded-2xl" />
      {/* Skeleton for ◆ REFERRAL_STATS card */}
      <Skeleton className="h-32 w-full rounded-2xl" />
      {/* Skeleton for ◆ MILESTONES card */}
      <Skeleton className="h-24 w-full rounded-2xl" />
    </div>
  )
}
```

RULE 10: Every dashboard page must have a loading.tsx sibling.
This skeleton renders during navigation while data fetches.
Do NOT use a spinner-only loading state.

═══════════════════════════════════════════════════════════════════
STEP 5 — VERIFICATION COMMANDS (Phase 3)
═══════════════════════════════════════════════════════════════════

INVOKE: Use /tailwindcss-animations

Run these exact grep commands and verify the expected counts:

# 1. Page structure — mono label ◆ REFERRAL_LINK
grep -c "◆ REFERRAL_LINK" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 2. Copy button with EXACTLY 2000ms timeout (2 seconds)
grep -c "setTimeout.*2000" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 3. Copy button state machine — COPY_LINK text
grep -c "COPY_LINK" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 4. Copy button state machine — COPIED! text (success state)
grep -c "COPIED!" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 5. Twitter/X share — correct intent URL
grep -c "twitter.com/intent/tweet" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 6. LinkedIn share — correct share-offsite URL
grep -c "linkedin.com/sharing/share-offsite" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 7. Stats card — mono label ◆ REFERRAL_STATS
grep -c "◆ REFERRAL_STATS" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 8. Stats — total referrals number in font-mono text-primary
grep -c 'font-mono text-4xl font-bold text-primary' app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 9. Progress bar — bg-primary rounded-full
grep -c "bg-primary rounded-full" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 10. Milestones — mono label ◆ MILESTONES
grep -c "◆ MILESTONES" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 11. Milestone reached indicator — CheckCircle2 text-success
grep -c "CheckCircle2.*text-success" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 12. Milestone next indicator — bg-warning (amber dot)
grep -c "bg-warning.*shrink-0" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 13. TanStack Query — useQuery with staleTime
grep -c "useQuery.*ReferralResponse" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1
grep -c "staleTime: 30_000" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 1

# 14. Loading state exists
ls app/\(dashboard\)/settings/referrals/loading.tsx 2>/dev/null && echo "EXISTS" || echo "MISSING"
Expected: EXISTS

# 15. No <form> tags (RULE 2: never use form tags)
grep -c "<form" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 0

# 16. No hardcoded hex colors (RULE: use CSS variables only)
grep -c "#2d4a3e\|#f5f3ee\|#ffc00d" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 0

# 17. Card radius — rounded-2xl (not rounded-lg)
grep -c "rounded-2xl" app/\(dashboard\)/settings/referrals/page.tsx
Expected: 3 (3 cards: link card, stats card, milestones card)

# 18. Copy button radius — rounded-full
grep -c "rounded-full" app/\(dashboard\)/settings/referrals/page.tsx
Expected: At least 1 (copy button)

═══════════════════════════════════════════════════════════════════
STEP 6 — AC-BY-AC VERIFICATION
═══════════════════════════════════════════════════════════════════

For each acceptance criterion, write a one-line verification result:

□ AC-1 (backend): Referral code auto-generated on user creation
  VERIFIED: grep -n "generate_referral_code" ravenbase-api/src/services/referral_service.py

□ AC-2 (backend): POST /v1/account/apply-referral sets referred_by_user_id
  VERIFIED: grep -n "apply-referral" ravenbase-api/src/api/routes/account.py

□ AC-3 (backend): Referee gets +200 signup_referral_bonus
  VERIFIED: grep -n "signup_referral_bonus" ravenbase-api/src/services/

□ AC-4 (backend): Referrer gets +200 on first Source creation
  VERIFIED: grep -n "award_referrer_on_first_upload" ravenbase-api/src/workers/tasks/

□ AC-5 (backend): referral_reward_claimed idempotency guard
  VERIFIED: grep -n "referral_reward_claimed" ravenbase-api/src/

□ AC-6 (backend): ReferralTransaction record created
  VERIFIED: grep -n "ReferralTransaction" ravenbase-api/src/models/

□ AC-7 (backend): Monthly cap 50 — skips if exceeded
  VERIFIED: grep -n "monthly_cap_reached\|>= 50" ravenbase-api/src/services/referral_service.py

□ AC-8 (backend): GET /v1/account/referral returns code, URL, stats
  VERIFIED: curl -s http://localhost:8000/v1/account/referral -H "Authorization: Bearer $TOKEN" | python -m json.tool

□ AC-9 (frontend): Settings → Referrals page with copy button, stats, milestones
  VERIFIED: grep -c "◆ REFERRAL_LINK" app/\(dashboard\)/settings/referrals/page.tsx = 1
  VERIFIED: grep -c "setTimeout.*2000" app/\(dashboard\)/settings/referrals/page.tsx = 1
  VERIFIED: grep -c "◆ MILESTONES" app/\(dashboard\)/settings/referrals/page.tsx = 1

□ AC-10 (backend): Case-insensitive referral code lookup
  VERIFIED: grep -n "\.upper()" ravenbase-api/src/services/referral_service.py

═══════════════════════════════════════════════════════════════════
ANTI-PATTERNS — automatic rejection (reject on sight)
═══════════════════════════════════════════════════════════════════

❌ className="rounded-lg" on any card → must be rounded-2xl
❌ className="rounded-md" on any button → must be rounded-full
❌ <form> tag anywhere → RULE 2: use onClick + controlled state, never <form>
❌ Hardcoded hex color (#2d4a3e, #f5f3ee, #ffc00d) → use CSS variables (bg-primary, bg-background, bg-warning)
❌ COPY_LINK text WITHOUT "COPIED!" success state → both states required
❌ setTimeout with 1000ms or 3000ms → must be exactly 2000ms (2 seconds)
❌ TanStack useState + useEffect for API data → RULE 6: must use useQuery/useMutation
❌ No loading.tsx sibling → RULE 10: every async dashboard page needs loading.tsx
❌ floating labels / placeholder-as-label → labels always ABOVE input
❌ bg-[#xxxx] anywhere → must use CSS variable token
❌ className="dark" or "light" on route group layout outer div

═══════════════════════════════════════════════════════════════════
SUCCESS CRITERIA — ALL must be YES to report complete
═══════════════════════════════════════════════════════════════════

INVOKE: Use /superpowers:verification-before-completion

✅ Referral link displayed in read-only input (font-mono text-sm bg-secondary)
✅ Copy button: "COPY_LINK" → "COPIED!" for exactly 2000ms (2 seconds)
✅ Copy button: Check icon + text-success in copied state, Copy icon + text-muted-foreground in default
✅ Twitter/X share button: correct intent URL opens in new tab (target="_blank" rel="noopener noreferrer")
✅ LinkedIn share button: correct share-offsite URL opens in new tab
✅ Stats: total referrals number in font-mono text-4xl text-primary
✅ Progress bar: bg-primary rounded-full fill toward next milestone
✅ Milestone timeline: CheckCircle2 text-success (reached), bg-warning (next), bg-secondary border (future)
✅ loading.tsx sibling exists with skeleton matching page structure
✅ TanStack Query: useQuery with staleTime: 30_000 (no useState+useEffect for API data)
✅ API response typed with ReferralResponse interface
✅ No <form> tags in the page
✅ No hardcoded hex colors in className strings
✅ All cards use rounded-2xl (not rounded-lg)
✅ npm run build passes (0 TypeScript errors)

Show plan first. Do not implement yet.
```

---

## Development Loop
Follow `docs/DEVELOPMENT_LOOP.md`.
```bash
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-034 referral system"
```
