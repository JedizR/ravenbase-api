# src/api/dependencies/admin.py
import structlog
from fastapi import Depends, HTTPException, Request

from src.api.dependencies.auth import require_user
from src.core.config import settings

logger = structlog.get_logger()


async def require_admin(user: dict = Depends(require_user)) -> dict:
    """Extend require_user with admin ID check.

    Admin user IDs come from ADMIN_USER_IDS env var (comma-separated Clerk user IDs).
    Returns 403 FORBIDDEN if the authenticated user is not in the admin set.
    """
    admin_ids = {uid.strip() for uid in settings.ADMIN_USER_IDS.split(",") if uid.strip()}
    if user["user_id"] not in admin_ids:
        logger.warning("admin.access_denied", user_id=user["user_id"])
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Admin access required"},
        )
    return user


async def get_arq_pool(request: Request):
    """Inject the ARQ Redis pool from app.state for the stats endpoint."""
    return request.app.state.arq_pool
