import jwt
import structlog
from fastapi import Header, HTTPException, Query

from src.core.config import settings

_clerk_jwks_client: jwt.PyJWKClient | None = None

logger = structlog.get_logger()


def _get_jwks_client() -> jwt.PyJWKClient:
    global _clerk_jwks_client
    if _clerk_jwks_client is None:
        jwks_url = f"https://{settings.CLERK_FRONTEND_API}/.well-known/jwks.json"
        _clerk_jwks_client = jwt.PyJWKClient(jwks_url)
    return _clerk_jwks_client


def _decode_jwt(token: str) -> dict:
    """Validate a Clerk JWT and return the user payload dict.

    Raises HTTPException 403 on any validation failure.
    """
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True},
        )
        # tier comes from Clerk's public_metadata.plan claim (set via Clerk Dashboard)
        tier = payload.get("public_metadata", {}).get("plan", "free")
        return {"user_id": payload["sub"], "email": payload.get("email", ""), "tier": tier}
    except jwt.ExpiredSignatureError as err:
        logger.warning("auth.token_expired")
        raise HTTPException(
            status_code=403,
            detail={"code": "TOKEN_EXPIRED", "message": "Token has expired"},
        ) from err
    except jwt.PyJWTError:
        logger.warning("auth.invalid_token")
        raise HTTPException(
            status_code=403,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        ) from None


async def require_user(authorization: str | None = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "MISSING_AUTH", "message": "Authorization header required"},
        )
    token = authorization.removeprefix("Bearer ")
    return _decode_jwt(token)


async def verify_token_query_param(token: str = Query(...)) -> dict:
    """JWT auth for EventSource connections that cannot set headers.

    EventSource passes the Clerk JWT as ?token=<jwt> in the query string.
    Validation logic is identical to require_user.
    """
    return _decode_jwt(token)
