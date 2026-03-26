# tests/unit/api/test_auth_query_param.py
"""Unit tests for verify_token_query_param dependency."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

FAKE_PAYLOAD = {
    "sub": "user_abc",
    "email": "test@example.com",
    "public_metadata": {"plan": "pro"},
}


@pytest.mark.asyncio
async def test_verify_token_query_param_valid_token():
    """Valid token → returns user dict with user_id, email, tier."""
    from src.api.dependencies.auth import verify_token_query_param  # noqa: PLC0415

    mock_key = MagicMock()
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_key

    with (
        patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client),
        patch("jwt.decode", return_value=FAKE_PAYLOAD),
    ):
        result = await verify_token_query_param(token="fake.jwt.token")

    assert result["user_id"] == "user_abc"
    assert result["email"] == "test@example.com"
    assert result["tier"] == "pro"


@pytest.mark.asyncio
async def test_verify_token_query_param_expired_token():
    """Expired token → 403 TOKEN_EXPIRED."""
    import jwt as pyjwt  # noqa: PLC0415

    from src.api.dependencies.auth import verify_token_query_param  # noqa: PLC0415

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock()

    with (
        patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client),
        patch("jwt.decode", side_effect=pyjwt.ExpiredSignatureError("expired")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await verify_token_query_param(token="expired.jwt.token")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_verify_token_query_param_invalid_token():
    """Garbage token → 403 INVALID_TOKEN."""
    import jwt as pyjwt  # noqa: PLC0415

    from src.api.dependencies.auth import verify_token_query_param  # noqa: PLC0415

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.side_effect = pyjwt.PyJWTError("bad token")

    with patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_info:
            await verify_token_query_param(token="garbage")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_verify_token_query_param_free_tier_default():
    """Token without public_metadata.plan → tier defaults to 'free'."""
    from src.api.dependencies.auth import verify_token_query_param  # noqa: PLC0415

    payload_no_tier = {"sub": "user_xyz", "email": "x@x.com"}
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock()

    with (
        patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client),
        patch("jwt.decode", return_value=payload_no_tier),
    ):
        result = await verify_token_query_param(token="fake.jwt.token")

    assert result["tier"] == "free"
