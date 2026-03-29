# tests/unit/test_auth_dependency.py
"""Unit tests for src/api/dependencies/auth.py.

Tests exercise require_user, verify_token_query_param, and _decode_jwt
without hitting a real Clerk JWKS endpoint.
"""

from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from src.api.dependencies.auth import _decode_jwt, require_user, verify_token_query_param

# ---------------------------------------------------------------------------
# require_user — header-based auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_user_no_header_returns_401():
    mock_request = MagicMock()
    mock_request.state = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await require_user(mock_request, authorization=None)
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "MISSING_AUTH"


@pytest.mark.asyncio
async def test_require_user_non_bearer_returns_401():
    mock_request = MagicMock()
    mock_request.state = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await require_user(mock_request, authorization="Token abc123")
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "MISSING_AUTH"


@pytest.mark.asyncio
async def test_require_user_valid_token_returns_user_dict():
    mock_payload = {
        "sub": "user_2vKdE5KqDemoClerkId",
        "email": "alice@example.com",
        "public_metadata": {"plan": "pro"},
    }
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock()

    mock_request = MagicMock()
    mock_request.state = MagicMock()
    with patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client):
        with patch("jwt.decode", return_value=mock_payload):
            result = await require_user(mock_request, authorization="Bearer valid.jwt.here")

    assert result == {
        "user_id": "user_2vKdE5KqDemoClerkId",
        "email": "alice@example.com",
        "tier": "pro",
    }


@pytest.mark.asyncio
async def test_require_user_missing_plan_defaults_to_free():
    mock_payload = {
        "sub": "user_abc",
        "email": "bob@example.com",
        "public_metadata": {},
    }
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock()

    mock_request = MagicMock()
    mock_request.state = MagicMock()
    with patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client):
        with patch("jwt.decode", return_value=mock_payload):
            result = await require_user(mock_request, authorization="Bearer valid.jwt.here")

    assert result["tier"] == "free"


# ---------------------------------------------------------------------------
# _decode_jwt — error paths
# ---------------------------------------------------------------------------


def test_decode_jwt_expired_returns_403_token_expired():
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock()

    with patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client):
        with patch("jwt.decode", side_effect=jwt.ExpiredSignatureError):
            with pytest.raises(HTTPException) as exc:
                _decode_jwt("expired.jwt.token")

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "TOKEN_EXPIRED"


def test_decode_jwt_invalid_returns_403_invalid_token():
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.side_effect = jwt.exceptions.DecodeError("bad")

    with patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc:
            _decode_jwt("garbage")

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "INVALID_TOKEN"


# ---------------------------------------------------------------------------
# verify_token_query_param — SSE auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_token_query_param_missing_returns_401():
    with pytest.raises(HTTPException) as exc:
        await verify_token_query_param(token=None)
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "MISSING_AUTH"


@pytest.mark.asyncio
async def test_verify_token_query_param_valid_returns_user_dict():
    mock_payload = {
        "sub": "user_sse_demo",
        "email": "sse@example.com",
        "public_metadata": {},
    }
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock()

    with patch("src.api.dependencies.auth._get_jwks_client", return_value=mock_client):
        with patch("jwt.decode", return_value=mock_payload):
            result = await verify_token_query_param(token="valid.sse.token")

    assert result["user_id"] == "user_sse_demo"
