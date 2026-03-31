# tests/integration/api/test_webhooks_stripe.py
"""Integration tests for POST /webhooks/stripe.

All DB calls are mocked via dependency_overrides.
stripe.Webhook.construct_event is patched so no real Stripe keys are needed.
Redis is mocked via app.state.redis injection.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.db import get_db
from src.api.main import app
from src.models.user import User

_STRIPE_SIG_HEADER = "t=1711584000,v1=fake_signature"

_TIER_UPGRADE_SESSION = {
    "id": "cs_test_upgrade_001",
    "object": "checkout.session",
    "metadata": {
        "user_id": "user_stripe_test_001",
        "tier": "pro",
        "period": "monthly",
        "session_type": "tier_upgrade",
    },
}

_CHECKOUT_COMPLETED_UPGRADE_EVENT = {
    "id": "evt_stripe_upgrade_001",
    "type": "checkout.session.completed",
    "data": {
        "object": _TIER_UPGRADE_SESSION,
    },
}

_DUPLICATE_EVENT_ID = "evt_stripe_duplicate_001"

_DUPLICATE_EVENT = {
    "id": _DUPLICATE_EVENT_ID,
    "type": "checkout.session.completed",
    "data": {
        "object": {
            "id": "cs_test_dup_001",
            "object": "checkout.session",
            "metadata": {
                "user_id": "user_dup_001",
                "tier": "pro",
                "session_type": "tier_upgrade",
            },
        }
    },
}


@pytest.fixture
async def stripe_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_redis():
    """Returns a fresh AsyncMock Redis client for each test."""
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=False)
    redis.setex = AsyncMock()
    return redis


@pytest.mark.asyncio
async def test_missing_stripe_signature_returns_400(stripe_client):
    """Request without stripe-signature header must be rejected with 400."""
    resp = await stripe_client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_WEBHOOK"


@pytest.mark.asyncio
async def test_invalid_stripe_signature_returns_400(stripe_client):
    """Request with a bad signature must be rejected with 400."""
    with patch("src.api.routes.webhooks.stripe.Webhook.construct_event") as mock_construct:
        mock_construct.side_effect = stripe.SignatureVerificationError(
            "No signatures found matching the expected signature", sig_header=_STRIPE_SIG_HEADER
        )
        resp = await stripe_client.post(
            "/webhooks/stripe",
            content=b'{"id":"evt_bad","type":"checkout.session.completed"}',
            headers={
                "content-type": "application/json",
                "stripe-signature": _STRIPE_SIG_HEADER,
            },
        )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
async def test_duplicate_event_returns_200_already_processed(stripe_client, mock_redis):
    """If Redis key already exists for this event, return 200 {"status": "already_processed"}."""
    mock_redis.exists = AsyncMock(return_value=True)

    # Inject the mock redis into app.state
    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis

    body = json.dumps(_DUPLICATE_EVENT).encode()

    try:
        with patch("src.api.routes.webhooks.stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = _DUPLICATE_EVENT

            resp = await stripe_client.post(
                "/webhooks/stripe",
                content=body,
                headers={
                    "content-type": "application/json",
                    "stripe-signature": _STRIPE_SIG_HEADER,
                },
            )
    finally:
        app.state.redis = original_redis

    assert resp.status_code == 200
    assert resp.json() == {"status": "already_processed"}

    mock_redis.exists.assert_awaited_once_with(f"stripe:event:{_DUPLICATE_EVENT_ID}")
    mock_redis.setex.assert_not_awaited()


@pytest.mark.asyncio
async def test_tier_upgrade_updates_user_tier(stripe_client, mock_redis):
    """checkout.session.completed with session_type=tier_upgrade must update user.tier."""
    user_id = "user_stripe_test_001"
    existing_user = User(
        id=user_id,
        email="billing@example.com",
        referral_code="TESTCODE",
        tier="free",
    )

    mock_db = AsyncMock()

    # exec() returns an object whose .first() gives the user
    exec_result = MagicMock()
    exec_result.first = MagicMock(return_value=existing_user)
    mock_db.exec = AsyncMock(return_value=exec_result)

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db

    original_redis = getattr(app.state, "redis", None)
    app.state.redis = mock_redis

    body = json.dumps(_CHECKOUT_COMPLETED_UPGRADE_EVENT).encode()

    try:
        with patch("src.api.routes.webhooks.stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = _CHECKOUT_COMPLETED_UPGRADE_EVENT

            resp = await stripe_client.post(
                "/webhooks/stripe",
                content=body,
                headers={
                    "content-type": "application/json",
                    "stripe-signature": _STRIPE_SIG_HEADER,
                },
            )
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.state.redis = original_redis

    assert resp.status_code == 200
    assert resp.json() == {"status": "processed"}

    # User.tier must have been set to "pro"
    assert existing_user.tier == "pro"
    mock_db.add.assert_called_once_with(existing_user)
    mock_db.commit.assert_awaited_once()

    # Idempotency key must be set after successful DB write
    mock_redis.setex.assert_awaited_once_with(
        f"stripe:event:{_CHECKOUT_COMPLETED_UPGRADE_EVENT['id']}",
        86400,
        "1",
    )
