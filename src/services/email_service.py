# src/services/email_service.py
"""Minimal EmailService for STORY-037 inactivity warning email.

resend is imported lazily (RULE 6). Email failure is NEVER fatal.
"""
import structlog

from src.core.config import settings
from src.services.base import BaseService

logger = structlog.get_logger()

_WARNING_BODY = """\
Hi {name},

We noticed you haven't used Ravenbase in 150 days.

As a Free-tier user, your stored data (documents, vectors, and knowledge graph) \
will be permanently deleted in 30 days if your account remains inactive.

To keep your data, log back into Ravenbase:
https://ravenbase.app/dashboard

If you no longer need your account, no action is required.

— The Ravenbase Team
"""


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
        name = display_name or to_email.split("@")[0]
        body = _WARNING_BODY.format(name=name)

        try:
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": "Ravenbase <noreply@ravenbase.app>",
                "to": [to_email],
                "subject": "Your Ravenbase data will be archived in 30 days",
                "text": body,
            })
            log.info("email.deletion_warning.sent")
            return True
        except Exception as exc:
            log.error("email.deletion_warning.failed", error=str(exc))
            return False
