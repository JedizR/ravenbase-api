# STORY-032: Transactional Email System (Resend + React Email)

**Epic:** EPIC-08 — Polish & Production Hardening
**Priority:** P1
**Complexity:** Medium
**Depends on:** STORY-018 (Clerk auth + user.created webhook must exist)

---

## Functional Requirements
<!-- Which FR acceptance criteria does this story satisfy? -->
None — transactional email story.

## Component
UI/Polish

---

> **Before You Start This Story — Read These Files First:**
> 1. `CLAUDE.md` — architecture rules (backend: 3-layer pattern, lazy imports)
> 2. `docs/architecture/05-security-privacy.md` — PII handling; never log email content
> 3. `docs/stories/EPIC-06-auth-profiles/STORY-018.md` — Clerk webhook setup (this story extends it)
> 4. `docs/stories/EPIC-08-polish/STORY-023.md` — Credit system (low-credits trigger uses credit balance)

---

## User Story
As a new user, I want to receive a welcome email after signing up so I know my account is active.
As a power user, I want to be warned when my credits are running low so I can upgrade before hitting a wall.
As any user who uploads a large file, I want a completion notification when processing finishes.

## Context
- Email provider: **Resend** (resend.com) — developer-friendly, App Router native, free tier: 3,000 emails/month
- Template engine: **React Email** (`@react-email/components`) — Resend's companion library for React-based email templates
- All emails are triggered server-side — never from frontend code
- Trigger points:
  1. **Welcome email** — Clerk webhook `user.created` fires (STORY-018 webhook handler)
  2. **Low credits warning** — credit balance drops below 10% of monthly allocation
  3. **Ingestion complete** — source file > 2MB finishes processing (large files only — small files are instant and don't need notification)
- PII rule: email addresses are the only PII in email payloads. Never log email content. Never include memory content in emails.

## Acceptance Criteria
- [ ] AC-1: New user receives a welcome email within 30 seconds of `user.created` Clerk webhook firing
- [ ] AC-2: Welcome email contains: Ravenbase logo, user's first name (from Clerk), a "Get started" CTA linking to `/dashboard`, and a one-line tagline matching brand voice
- [ ] AC-3: When a user's credit balance drops to < 10% of their plan's monthly allocation, a low-credits warning email is sent (once per billing period — not every single deduction)
- [ ] AC-4: When a source file > 2MB completes Docling processing (status = COMPLETED), an ingestion complete notification is sent
- [ ] AC-5: All emails are branded: `from: "Ravenbase <hello@ravenbase.app>"` with Ravenbase logo in header, primary color (#2d4a3e) for CTAs, warm cream (#f5f3ee) background
- [ ] AC-6: Failed email sends are logged with structlog at `error` level but never crash the triggering operation — email failure is non-fatal
- [ ] AC-7: `RESEND_API_KEY` environment variable controls sending; if absent, emails are skipped with a `warning` log (allows development without sending real emails)
- [ ] AC-8: No email is sent during test runs (`APP_ENV=test`)
- [ ] AC-9: `POST /webhooks/resend` handles `email.bounced`: disables the specific `notify_*` flag for that user based on which email type bounced (determined by email subject match). Logs `email.bounced` at `warning` level.
- [ ] AC-10: `POST /webhooks/resend` handles `email.complained` (spam report): sets ALL THREE `notify_*` flags to `False` — spam complaint is more severe than a bounce and indicates the user doesn't want ANY emails. Logs `email.complained` at `warning` level.
- [ ] AC-11: Resend webhook signature validated using `svix` library (same pattern as Clerk webhook in STORY-018). Reject unauthenticated requests with `403`.

## Technical Notes

### Stack
- Provider: Resend (`resend` Python SDK from PyPI)
- Templates: HTML strings styled with inline CSS (React Email is frontend-only; use plain HTML strings in Python backend)
- Sending: async via `resend.Emails.send_async()` — never blocks the request lifecycle

### Files to Create
- `src/services/email_service.py` — EmailService with send_welcome, send_low_credits, send_ingestion_complete
- `src/adapters/resend_adapter.py` — thin wrapper around Resend Python SDK
- `src/templates/emails/welcome.py` — HTML template function returning email HTML string
- `src/templates/emails/low_credits.py` — HTML template function
- `src/templates/emails/ingestion_complete.py` — HTML template function
- `tests/unit/services/test_email_service.py`

### Files to Modify
- `src/api/routes/webhooks.py` — call `email_service.send_welcome()` inside `user.created` handler (after user is saved to DB)
- `src/workers/tasks/ingestion.py` — call `email_service.send_ingestion_complete()` when source > 2MB reaches COMPLETED
- `src/services/credit_service.py` — call `email_service.send_low_credits()` after deduction if balance < 10%
- `src/api/routes/webhooks.py` — add `POST /webhooks/resend` handler

### Resend Bounce & Complaint Webhook

```python
# POST /webhooks/resend — handles bounce and complaint events

@router.post("/webhooks/resend")
async def handle_resend_webhook(request: Request, db: AsyncSession):
    payload = await request.body()
    try:
        wh = Webhook(settings.RESEND_WEBHOOK_SECRET)
        event = wh.verify(payload, {
            "svix-id": request.headers.get("svix-id"),
            "svix-timestamp": request.headers.get("svix-timestamp"),
            "svix-signature": request.headers.get("svix-signature"),
        })
    except WebhookVerificationError:
        raise HTTPException(status_code=403)

    event_type = event.get("type")
    to_email = event.get("data", {}).get("email", {}).get("to", [None])[0]
    subject = event.get("data", {}).get("email", {}).get("subject", "")
    if not to_email:
        return {"status": "ignored"}

    user = (await db.execute(select(User).where(User.email == to_email))).scalar_one_or_none()
    if not user:
        return {"status": "user_not_found"}  # Return 200 — Resend retries on 5xx

    if event_type == "email.bounced":
        # Disable only the specific notification type
        if "welcome" in subject.lower():
            user.notify_welcome = False
        elif "credit" in subject.lower():
            user.notify_low_credits = False
        elif "processed" in subject.lower() or "complete" in subject.lower():
            user.notify_ingestion_complete = False
        await db.commit()
        log.warning("email.bounced", user_id=str(user.id), subject=subject)

    elif event_type == "email.complained":
        # Spam complaint — disable ALL notifications
        user.notify_welcome = False
        user.notify_low_credits = False
        user.notify_ingestion_complete = False
        await db.commit()
        log.warning("email.complained", user_id=str(user.id))

    return {"status": "handled"}
```

### EmailService Pattern

```python
# src/services/email_service.py
import os
from structlog import get_logger
from src.adapters.resend_adapter import ResendAdapter
from src.templates.emails.welcome import render_welcome_email
from src.templates.emails.low_credits import render_low_credits_email
from src.templates.emails.ingestion_complete import render_ingestion_complete_email

log = get_logger()

class EmailService:
    def __init__(self, resend: ResendAdapter | None = None):
        self._resend = resend or ResendAdapter()

    async def send_welcome(self, email: str, first_name: str, notify: bool = True) -> None:
        """Send welcome email to new user. Non-fatal — never raise."""
        if os.getenv("APP_ENV") == "test":
            return
        if not notify:
            log.info("email.skipped", reason="user_preference", type="welcome")
            return
        if not os.getenv("RESEND_API_KEY"):
            log.warning("email.skipped", reason="RESEND_API_KEY not set", type="welcome")
            return
        try:
            html = render_welcome_email(first_name=first_name)
            await self._resend.send(
                to=email,
                subject="Welcome to Ravenbase",
                html=html,
            )
            log.info("email.sent", type="welcome")
        except Exception as e:
            log.error("email.send_failed", type="welcome", error=str(e))
            # Never re-raise — email failure is non-fatal

    async def send_low_credits(self, email: str, balance: int, plan_limit: int, notify: bool = True) -> None:
        """Send low credits warning. Non-fatal."""
        if os.getenv("APP_ENV") == "test":
            return
        if not notify:
            log.info("email.skipped", reason="user_preference", type="low_credits")
            return
        if not os.getenv("RESEND_API_KEY"):
            log.warning("email.skipped", reason="RESEND_API_KEY not set", type="low_credits")
            return
        try:
            html = render_low_credits_email(balance=balance, plan_limit=plan_limit)
            await self._resend.send(
                to=email,
                subject=f"You have {balance} credits remaining — Ravenbase",
                html=html,
            )
            log.info("email.sent", type="low_credits", balance=balance)
        except Exception as e:
            log.error("email.send_failed", type="low_credits", error=str(e))

    async def send_ingestion_complete(
        self, email: str, filename: str, node_count: int, notify: bool = True
    ) -> None:
        """Send ingestion completion for large files (> 2MB). Non-fatal."""
        if os.getenv("APP_ENV") == "test":
            return
        if not notify:
            log.info("email.skipped", reason="user_preference", type="ingestion_complete")
            return
        if not os.getenv("RESEND_API_KEY"):
            return
        try:
            html = render_ingestion_complete_email(
                filename=filename, node_count=node_count
            )
            await self._resend.send(
                to=email,
                subject=f"✓ {filename} has been processed — Ravenbase",
                html=html,
            )
            log.info("email.sent", type="ingestion_complete", filename=filename)
        except Exception as e:
            log.error("email.send_failed", type="ingestion_complete", error=str(e))
```

### Email Template Pattern (plain Python HTML string)

```python
# src/templates/emails/welcome.py
BRAND_GREEN = "#2d4a3e"
BRAND_CREAM = "#f5f3ee"
BRAND_CARD = "#ffffff"

def render_welcome_email(first_name: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:{BRAND_CREAM};font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="560" cellpadding="0" cellspacing="0" style="background:{BRAND_CARD};border-radius:12px;overflow:hidden;">
        <!-- Header with primary green -->
        <tr><td style="background:{BRAND_GREEN};padding:32px 40px;">
          <p style="color:#ffffff;font-size:22px;font-weight:800;letter-spacing:0.1em;margin:0;font-family:Arial,sans-serif;">RAVENBASE</p>
          <p style="color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:0.15em;margin:4px 0 0;font-family:monospace;">WHAT HAPPENED, WHERE, AND WHEN. ALWAYS.</p>
        </td></tr>
        <!-- Body -->
        <tr><td style="padding:40px;">
          <h1 style="font-size:28px;color:#1a1a1a;margin:0 0 16px;font-family:Georgia,serif;">Welcome, {first_name}.</h1>
          <p style="font-size:16px;color:#374151;line-height:1.6;margin:0 0 24px;">
            Your exocortex is ready. Start by uploading your notes, chat exports, or documents — Ravenbase will build your knowledge graph automatically.
          </p>
          <a href="https://ravenbase.app/dashboard"
             style="display:inline-block;background:{BRAND_GREEN};color:#ffffff;text-decoration:none;
                    padding:14px 28px;border-radius:9999px;font-size:14px;font-weight:600;margin-bottom:32px;">
            Open Ravenbase
          </a>
          <p style="font-size:13px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:24px;margin:0;">
            You received this because you created a Ravenbase account.
            <a href="https://ravenbase.app/privacy" style="color:{BRAND_GREEN};">Privacy Policy</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
```

### Architecture Constraints
- Before sending any email, check the user's notification preference:
  - `send_welcome()` → only send if `user.notify_welcome is True`
  - `send_low_credits()` → only send if `user.notify_low_credits is True`
  - `send_ingestion_complete()` → only send if `user.notify_ingestion_complete is True`
  - The `user` object must be passed into each send method (already available from the calling context)
  - This check runs AFTER the `APP_ENV=test` check and AFTER the `RESEND_API_KEY` check
- `resend` Python SDK import must be lazy: `import resend  # noqa: PLC0415` inside the method body
- Email sending must be `async` — use `resend.Emails.send_async()` or wrap sync call with `asyncio.to_thread()`
- Never include memory content, conflict text, or document content in any email body
- Never log the `to` email address at any log level — only log `type` and `bool(success)`
- `send_low_credits()` must be called from credit_service only once per billing period — track in a `low_credits_email_sent_at` column on `User` model, reset on monthly credit refresh

### Environment Variable
```bash
# .envs/.env.dev — add this line:
RESEND_API_KEY=re_test_xxxxxxxxxxxx   # Get from resend.com → API Keys → Create API Key
# Leave blank to skip email sending in local development
```

### pyproject.toml
Add to dependencies:
```toml
"resend>=2.5.0",
```

## Definition of Done
- [ ] Welcome email sends successfully when Clerk `user.created` webhook fires
- [ ] Low credits email fires when balance < 10% (only once per billing period)
- [ ] Ingestion complete email fires for files > 2MB on COMPLETED status
- [ ] Failed sends log at error level but never raise (non-fatal)
- [ ] Emails skip when `APP_ENV=test`
- [ ] `make quality && make test` passes (0 errors, 0 failures)

## Testing This Story

```bash
# 1. Set RESEND_API_KEY in .envs/.env.dev (use test key from resend.com)
# 2. Trigger welcome email via Clerk webhook simulation:
stripe listen &   # or use ngrok for Clerk webhook
# Or call directly in a Python shell:
# from src.services.email_service import EmailService
# import asyncio
# asyncio.run(EmailService().send_welcome("your@email.com", "Jedi"))

# 3. Check Resend dashboard at resend.com/emails — verify email appears

# 4. Test skip behavior:
APP_ENV=test python3 -c "
import asyncio
from src.services.email_service import EmailService
asyncio.run(EmailService().send_welcome('test@test.com', 'Test'))
# Should log: email.skipped (not send)
"
```

---

## Agent Implementation Brief

```
Implement STORY-032: Transactional Email System.

Read first:
1. CLAUDE.md (architecture rules — RULE 6: heavy imports lazy, RULE 7: no print)
2. docs/architecture/05-security-privacy.md (PII rules)
3. docs/stories/EPIC-06-auth-profiles/STORY-018.md (webhook handler to extend)
4. docs/stories/EPIC-08-polish/STORY-032.md (this file)

Key constraints:
- resend import is LAZY (inside function body)
- Email failure is NEVER fatal — always catch and log, never re-raise
- Skip all sends when APP_ENV=test
- Never log email addresses
- welcome email: triggered from webhooks.py user.created handler
- low credits: triggered from credit_service.deduct() when balance < 10%
- ingestion complete: triggered from ingestion task when file > 2MB AND status = COMPLETED

Show plan first. Do not implement yet.
```

---

## Development Loop

Follow the full loop defined in `docs/DEVELOPMENT_LOOP.md`.

```bash
make quality && make test
git add -A && git commit -m "feat(ravenbase): STORY-032 transactional email system (Resend)"
git push
# Edit docs/stories/epics.md → 🔲 → ✅ for STORY-032
git add docs/stories/epics.md docs/.bmad/project-status.md
git commit -m "docs: mark STORY-032 complete"
git push
```
