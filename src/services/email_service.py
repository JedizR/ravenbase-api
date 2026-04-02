# src/services/email_service.py
"""EmailService for Ravenbase transactional emails (STORY-032).

resend is imported lazily (RULE 6). Email failure is NEVER fatal.
"""

from __future__ import annotations

import os

import structlog

from src.core.config import settings
from src.services.base import BaseService

logger = structlog.get_logger()

_WARNING_BODY = """\
Hi {name},

We noticed you haven't used Ravenbase in 85 days.

As a Free-tier user, your stored data (documents, vectors, and knowledge graph) \
will be permanently deleted in 5 days if your account remains inactive.

To keep your data, log back into Ravenbase:
https://ravenbase.app/dashboard

If you no longer need your account, no action is required.

— The Ravenbase Team
"""

# Brand colors for email templates
_BRAND_GREEN = "#2d4a3e"
_BRAND_CREAM = "#f5f3ee"
_BRAND_CARD = "#ffffff"


def _render_welcome_email(first_name: str) -> str:
    """Render the welcome email HTML template."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:{_BRAND_CREAM};font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="560" cellpadding="0" cellspacing="0" style="background:{_BRAND_CARD};border-radius:12px;overflow:hidden;">
        <tr><td style="background:{_BRAND_GREEN};padding:32px 40px;">
          <p style="color:#ffffff;font-size:22px;font-weight:800;letter-spacing:0.1em;margin:0;font-family:Arial,sans-serif;">RAVENBASE</p>
          <p style="color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:0.15em;margin:4px 0 0;font-family:monospace;">WHAT HAPPENED, WHERE, AND WHEN. ALWAYS.</p>
        </td></tr>
        <tr><td style="padding:40px;">
          <h1 style="font-size:28px;color:#1a1a1a;margin:0 0 16px;font-family:Georgia,serif;">Welcome, {first_name}.</h1>
          <p style="font-size:16px;color:#374151;line-height:1.6;margin:0 0 24px;">
            Your exocortex is ready. Start by uploading your notes, chat exports, or documents — Ravenbase will build your knowledge graph automatically.
          </p>
          <a href="https://ravenbase.app/dashboard"
             style="display:inline-block;background:{_BRAND_GREEN};color:#ffffff;text-decoration:none;
                    padding:14px 28px;border-radius:9999px;font-size:14px;font-weight:600;margin-bottom:32px;">
            Open Ravenbase
          </a>
          <p style="font-size:13px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:24px;margin:0;">
            You received this because you created a Ravenbase account.
            <a href="https://ravenbase.app/privacy" style="color:{_BRAND_GREEN};">Privacy Policy</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _render_low_credits_email(balance: int, plan_limit: int) -> str:
    """Render the low credits warning email HTML template."""
    pct = int(balance / plan_limit * 100) if plan_limit > 0 else 0
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:{_BRAND_CREAM};font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="560" cellpadding="0" cellspacing="0" style="background:{_BRAND_CARD};border-radius:12px;overflow:hidden;">
        <tr><td style="background:{_BRAND_GREEN};padding:32px 40px;">
          <p style="color:#ffffff;font-size:22px;font-weight:800;letter-spacing:0.1em;margin:0;font-family:Arial,sans-serif;">RAVENBASE</p>
          <p style="color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:0.15em;margin:4px 0 0;font-family:monospace;">WHAT HAPPENED, WHERE, AND WHEN. ALWAYS.</p>
        </td></tr>
        <tr><td style="padding:40px;">
          <h1 style="font-size:28px;color:#1a1a1a;margin:0 0 16px;font-family:Georgia,serif;">Running low on credits.</h1>
          <p style="font-size:16px;color:#374151;line-height:1.6;margin:0 0 24px;">
            You have <strong>{balance} credits</strong> remaining — that's {pct}% of your plan allocation.
            Upgrade to Pro to keep your exocortex growing without interruption.
          </p>
          <!-- Credit usage bar -->
          <div style="background:#e8ebe6;border-radius:9999px;height:8px;width:100%;margin-bottom:24px;">
            <div style="background:{_BRAND_GREEN};border-radius:9999px;height:8px;width:{pct}%;"></div>
          </div>
          <a href="https://ravenbase.app/settings/billing"
             style="display:inline-block;background:{_BRAND_GREEN};color:#ffffff;text-decoration:none;
                    padding:14px 28px;border-radius:9999px;font-size:14px;font-weight:600;margin-bottom:32px;">
            Upgrade to Pro
          </a>
          <p style="font-size:13px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:24px;margin:0;">
            Your credits reset at the start of each billing cycle.
            <a href="https://ravenbase.app/privacy" style="color:{_BRAND_GREEN};">Privacy Policy</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _render_ingestion_complete_email(filename: str, node_count: int) -> str:
    """Render the ingestion complete email HTML template."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:{_BRAND_CREAM};font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="560" cellpadding="0" cellspacing="0" style="background:{_BRAND_CARD};border-radius:12px;overflow:hidden;">
        <tr><td style="background:{_BRAND_GREEN};padding:32px 40px;">
          <p style="color:#ffffff;font-size:22px;font-weight:800;letter-spacing:0.1em;margin:0;font-family:Arial,sans-serif;">RAVENBASE</p>
          <p style="color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:0.15em;margin:4px 0 0;font-family:monospace;">WHAT HAPPENED, WHERE, AND WHEN. ALWAYS.</p>
        </td></tr>
        <tr><td style="padding:40px;">
          <h1 style="font-size:28px;color:#1a1a1a;margin:0 0 16px;font-family:Georgia,serif;">{filename} — processed.</h1>
          <p style="font-size:16px;color:#374151;line-height:1.6;margin:0 0 24px;">
            Your document has been indexed. <strong>{node_count} memory nodes</strong> have been extracted and added to your knowledge graph.
          </p>
          <a href="https://ravenbase.app/graph"
             style="display:inline-block;background:{_BRAND_GREEN};color:#ffffff;text-decoration:none;
                    padding:14px 28px;border-radius:9999px;font-size:14px;font-weight:600;margin-bottom:32px;">
            View Knowledge Graph
          </a>
          <p style="font-size:13px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:24px;margin:0;">
            You received this because a large file (over 2MB) finished processing.
            <a href="https://ravenbase.app/privacy" style="color:{_BRAND_GREEN};">Privacy Policy</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


class EmailService(BaseService):
    async def send_account_deletion_warning(
        self,
        *,
        to_email: str,
        display_name: str | None,
        user_id: str,
    ) -> bool:
        """Send 150-day inactivity warning. Non-fatal — returns False on failure."""
        import resend  # noqa: PLC0415

        log = logger.bind(tenant_id=user_id, action="email.deletion_warning")
        name = display_name or to_email.split("@", maxsplit=1)[0]
        body = _WARNING_BODY.format(name=name)

        try:
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send(
                {
                    "from": "Ravenbase <noreply@ravenbase.app>",
                    "to": [to_email],
                    "subject": "Your Ravenbase data will be deleted in 5 days",
                    "text": body,
                }
            )
            log.info("email.deletion_warning.sent")
            return True
        except Exception as exc:
            log.error("email.deletion_warning.failed", error=str(exc))
            return False

    async def send_welcome(
        self,
        *,
        email: str,
        first_name: str,
        notify: bool = True,
    ) -> None:
        """Send welcome email to new user. Non-fatal — never raise."""
        import resend  # noqa: PLC0415

        log = logger.bind(action="email.welcome", to_email_hash=hash(email) % 10_000)
        if os.getenv("APP_ENV") == "test":
            log.info("email.skipped", reason="APP_ENV=test")
            return
        if not notify:
            log.info("email.skipped", reason="user_preference")
            return
        if not settings.RESEND_API_KEY:
            log.warning("email.skipped", reason="RESEND_API_KEY not set")
            return
        try:
            html = _render_welcome_email(first_name=first_name)
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send(
                {
                    "from": "Ravenbase <hello@ravenbase.app>",
                    "to": [email],
                    "subject": "Welcome to Ravenbase",
                    "html": html,
                }
            )
            log.info("email.sent", type="welcome")
        except Exception as exc:
            log.error("email.send_failed", type="welcome", error=str(exc))
            # Never re-raise — email failure is non-fatal

    async def send_low_credits(
        self,
        *,
        email: str,
        balance: int,
        plan_limit: int,
        notify: bool = True,
    ) -> None:
        """Send low credits warning. Non-fatal — never raise."""
        import resend  # noqa: PLC0415

        log = logger.bind(action="email.low_credits", to_email_hash=hash(email) % 10_000)
        if os.getenv("APP_ENV") == "test":
            log.info("email.skipped", reason="APP_ENV=test")
            return
        if not notify:
            log.info("email.skipped", reason="user_preference")
            return
        if not settings.RESEND_API_KEY:
            log.warning("email.skipped", reason="RESEND_API_KEY not set")
            return
        try:
            html = _render_low_credits_email(balance=balance, plan_limit=plan_limit)
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send(
                {
                    "from": "Ravenbase <hello@ravenbase.app>",
                    "to": [email],
                    "subject": f"You have {balance} credits remaining — Ravenbase",
                    "html": html,
                }
            )
            log.info("email.sent", type="low_credits", balance=balance)
        except Exception as exc:
            log.error("email.send_failed", type="low_credits", error=str(exc))

    async def send_ingestion_complete(
        self,
        *,
        email: str,
        filename: str,
        node_count: int,
        notify: bool = True,
    ) -> None:
        """Send ingestion completion for large files (>2MB). Non-fatal — never raise."""
        import resend  # noqa: PLC0415

        log = logger.bind(action="email.ingestion_complete", to_email_hash=hash(email) % 10_000)
        if os.getenv("APP_ENV") == "test":
            log.info("email.skipped", reason="APP_ENV=test")
            return
        if not notify:
            log.info("email.skipped", reason="user_preference")
            return
        if not settings.RESEND_API_KEY:
            log.warning("email.skipped", reason="RESEND_API_KEY not set")
            return
        try:
            html = _render_ingestion_complete_email(filename=filename, node_count=node_count)
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send(
                {
                    "from": "Ravenbase <hello@ravenbase.app>",
                    "to": [email],
                    "subject": f"✓ {filename} has been processed — Ravenbase",
                    "html": html,
                }
            )
            log.info(
                "email.sent", type="ingestion_complete", filename=filename, node_count=node_count
            )
        except Exception as exc:
            log.error("email.send_failed", type="ingestion_complete", error=str(exc))

    async def send_export_complete(
        self,
        *,
        email: str,
        download_url: str,
        notify: bool = True,
    ) -> None:
        """Send data export ready notification with download link. Non-fatal — never raise."""
        import resend  # noqa: PLC0415

        log = logger.bind(action="email.export_complete", to_email_hash=hash(email) % 10_000)
        if os.getenv("APP_ENV") == "test":
            log.info("email.skipped", reason="APP_ENV=test")
            return
        if not notify:
            log.info("email.skipped", reason="user_preference")
            return
        if not settings.RESEND_API_KEY:
            log.warning("email.skipped", reason="RESEND_API_KEY not set")
            return
        try:
            html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:{_BRAND_CREAM};font-family:'DM Sans',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="560" cellpadding="0" cellspacing="0" style="background:{_BRAND_CARD};border-radius:12px;overflow:hidden;">
        <tr><td style="background:{_BRAND_GREEN};padding:32px 40px;">
          <p style="color:#ffffff;font-size:22px;font-weight:800;letter-spacing:0.1em;margin:0;font-family:Arial,sans-serif;">RAVENBASE</p>
          <p style="color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:0.15em;margin:4px 0 0;font-family:monospace;">WHAT HAPPENED, WHERE, AND WHEN. ALWAYS.</p>
        </td></tr>
        <tr><td style="padding:40px;">
          <h1 style="font-size:28px;color:#1a1a1a;margin:0 0 16px;font-family:Georgia,serif;">Your data export is ready.</h1>
          <p style="font-size:16px;color:#374151;line-height:1.6;margin:0 0 24px;">
            Your data export has been prepared and is available for download. The download link will expire in 24 hours.
          </p>
          <a href="{download_url}"
             style="display:inline-block;background:{_BRAND_GREEN};color:#ffffff;text-decoration:none;
                    padding:14px 28px;border-radius:9999px;font-size:14px;font-weight:600;margin-bottom:32px;">
            Download Your Data
          </a>
          <p style="font-size:13px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:24px;margin:0;">
            You received this because you requested a data export from Ravenbase.
            <a href="https://ravenbase.app/privacy" style="color:{_BRAND_GREEN};">Privacy Policy</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send(
                {
                    "from": "Ravenbase <hello@ravenbase.app>",
                    "to": [email],
                    "subject": "Your Ravenbase data export is ready",
                    "html": html,
                }
            )
            log.info("email.sent", type="export_complete")
        except Exception as exc:
            log.error("email.send_failed", type="export_complete", error=str(exc))
