# tests/integration/api/test_webhooks_endpoint.py
"""Integration tests for POST /webhooks/clerk.

All DB calls are mocked. svix verification is patched.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from svix.webhooks import WebhookVerificationError

from src.api.dependencies.db import get_db
from src.api.main import app
from src.models.user import User

_USER_CREATED_PAYLOAD = {
    "type": "user.created",
    "data": {
        "id": "user_2vKdE5KqDemoClerkId",
        "email_addresses": [{"id": "iead_abc123", "email_address": "newuser@example.com"}],
        "primary_email_address_id": "iead_abc123",
        "first_name": "New",
        "last_name": "User",
        "image_url": "https://img.clerk.com/avatar.jpg",
    },
}

_SVIX_HEADERS = {
    "content-type": "application/json",
    "svix-id": "msg_2vKdE5KqDemo",
    "svix-timestamp": "1711584000",
    "svix-signature": "v1,valid_signature_here",
}


@pytest.fixture
async def webhook_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_missing_svix_headers_returns_400(webhook_client):
    resp = await webhook_client.post(
        "/webhooks/clerk",
        content=b"{}",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_WEBHOOK"


@pytest.mark.asyncio
async def test_invalid_signature_returns_400(webhook_client):
    with patch("src.api.routes.webhooks.Webhook") as mock_cls:
        mock_wh = MagicMock()
        mock_wh.verify.side_effect = WebhookVerificationError("bad sig")
        mock_cls.return_value = mock_wh

        resp = await webhook_client.post(
            "/webhooks/clerk",
            content=b"{}",
            headers=_SVIX_HEADERS,
        )

    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
async def test_user_created_inserts_user(webhook_client):
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)  # user does not yet exist

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db

    body = json.dumps(_USER_CREATED_PAYLOAD).encode()

    with (
        patch("src.api.routes.webhooks.Webhook") as mock_cls,
        patch("src.api.routes.webhooks.CreditService") as mock_credit_cls,
    ):
        mock_wh = MagicMock()
        mock_wh.verify.return_value = _USER_CREATED_PAYLOAD
        mock_cls.return_value = mock_wh

        mock_credit_svc = AsyncMock()
        mock_credit_cls.return_value = mock_credit_svc

        resp = await webhook_client.post("/webhooks/clerk", content=body, headers=_SVIX_HEADERS)

    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    mock_db.add.assert_called_once()
    created_user: User = mock_db.add.call_args[0][0]
    assert created_user.id == "user_2vKdE5KqDemoClerkId"
    assert created_user.email == "newuser@example.com"
    assert created_user.display_name == "New User"
    assert created_user.avatar_url == "https://img.clerk.com/avatar.jpg"
    assert len(created_user.referral_code) == 8
    assert created_user.referral_code == created_user.referral_code.upper()
    mock_db.commit.assert_called_once()
    mock_credit_svc.add_credits.assert_awaited_once_with(
        mock_db, "user_2vKdE5KqDemoClerkId", 500, "signup_bonus"
    )


@pytest.mark.asyncio
async def test_user_created_idempotent_if_user_exists(webhook_client):
    """Second webhook for same user must not create a duplicate."""
    existing = User(
        id="user_2vKdE5KqDemoClerkId",
        email="newuser@example.com",
        referral_code="ABCD1234",
    )
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=existing)

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db

    body = json.dumps(_USER_CREATED_PAYLOAD).encode()

    with patch("src.api.routes.webhooks.Webhook") as mock_cls:
        mock_wh = MagicMock()
        mock_wh.verify.return_value = _USER_CREATED_PAYLOAD
        mock_cls.return_value = mock_wh

        resp = await webhook_client.post("/webhooks/clerk", content=body, headers=_SVIX_HEADERS)

    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_event_type_returns_ok(webhook_client):
    """Non-user.created events are silently ignored."""
    payload = {"type": "session.created", "data": {}}

    with patch("src.api.routes.webhooks.Webhook") as mock_cls:
        mock_wh = MagicMock()
        mock_wh.verify.return_value = payload
        mock_cls.return_value = mock_wh

        resp = await webhook_client.post(
            "/webhooks/clerk",
            content=json.dumps(payload).encode(),
            headers=_SVIX_HEADERS,
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
