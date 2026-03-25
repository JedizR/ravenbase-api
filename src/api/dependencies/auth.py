import jwt
from fastapi import Header, HTTPException

from src.core.config import settings

_clerk_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _clerk_jwks_client
    if _clerk_jwks_client is None:
        jwks_url = f"https://{settings.CLERK_FRONTEND_API}/.well-known/jwks.json"
        _clerk_jwks_client = jwt.PyJWKClient(jwks_url)
    return _clerk_jwks_client


async def require_user(authorization: str | None = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "MISSING_AUTH", "message": "Authorization header required"},
        )
    token = authorization.removeprefix("Bearer ")
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True},
        )
        return {"user_id": payload["sub"], "email": payload.get("email", "")}
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=403,
            detail={"code": "TOKEN_EXPIRED", "message": "Token has expired"},
        ) from err
    except Exception:
        raise HTTPException(
            status_code=403,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
        ) from None
