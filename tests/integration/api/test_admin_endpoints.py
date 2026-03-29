# tests/integration/api/test_admin_endpoints.py
"""Integration tests for STORY-036-BE Admin API endpoints.

All external dependencies mocked. Follows test_chat_endpoints.py pattern.
"""
from datetime import UTC, datetime

import pytest
from src.schemas.admin import (
    AdminStatsResponse,
    AdminTransactionOut,
    AdminUserDetailResponse,
    AdminUserListResponse,
    AdminUserOut,
    CreditAdjustRequest,
    CreditAdjustResponse,
    ToggleActiveRequest,
    ToggleActiveResponse,
)


def test_admin_user_out_schema() -> None:
    now = datetime.now(UTC)
    u = AdminUserOut(
        id="user_1",
        email="a@b.com",
        display_name="Alice",
        tier="free",
        credits_balance=100,
        is_active=True,
        created_at=now,
        last_active_at=None,
    )
    assert u.id == "user_1"
    assert u.last_active_at is None


def test_admin_user_list_response_schema() -> None:
    now = datetime.now(UTC)
    resp = AdminUserListResponse(
        users=[
            AdminUserOut(
                id="u1",
                email="a@b.com",
                display_name=None,
                tier="free",
                credits_balance=0,
                is_active=True,
                created_at=now,
                last_active_at=None,
            )
        ],
        total=1,
        page=1,
    )
    assert resp.total == 1
    assert len(resp.users) == 1


def test_credit_adjust_request_schema() -> None:
    req = CreditAdjustRequest(user_id="u1", amount=50, reason="bonus")
    assert req.amount == 50
    req_neg = CreditAdjustRequest(user_id="u1", amount=-25, reason="correction")
    assert req_neg.amount == -25


def test_admin_stats_response_schema() -> None:
    stats = AdminStatsResponse(
        total_users=100,
        active_today=10,
        new_today=5,
        pro_users=3,
        daily_llm_spend_usd=12.50,
        llm_spend_cap_usd=50.0,
        sources_today=7,
        metadocs_today=2,
    )
    assert stats.daily_llm_spend_usd == 12.50
    assert stats.llm_spend_cap_usd == 50.0


@pytest.mark.asyncio
async def test_require_admin_blocks_non_admin(mocker) -> None:
    mocker.patch(
        "src.api.dependencies.admin.settings",
        type("S", (), {"ADMIN_USER_IDS": "admin_aaa,admin_bbb"})(),
    )
    from src.api.dependencies.admin import require_admin  # noqa: PLC0415

    with pytest.raises(Exception) as exc_info:
        await require_admin({"user_id": "not_an_admin", "email": "x@x.com", "tier": "free"})
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_require_admin_allows_admin_user(mocker) -> None:
    mocker.patch(
        "src.api.dependencies.admin.settings",
        type("S", (), {"ADMIN_USER_IDS": "admin_aaa,admin_bbb"})(),
    )
    from src.api.dependencies.admin import require_admin  # noqa: PLC0415

    result = await require_admin({"user_id": "admin_aaa", "email": "admin@test.com", "tier": "free"})
    assert result["user_id"] == "admin_aaa"


@pytest.mark.asyncio
async def test_require_admin_blocks_when_admin_ids_empty(mocker) -> None:
    mocker.patch(
        "src.api.dependencies.admin.settings",
        type("S", (), {"ADMIN_USER_IDS": ""})(),
    )
    from src.api.dependencies.admin import require_admin  # noqa: PLC0415

    with pytest.raises(Exception) as exc_info:
        await require_admin({"user_id": "any_user", "email": "x@x.com", "tier": "free"})
    assert exc_info.value.status_code == 403


# ── /v1/admin/users (list) ──────────────────────────────────────────────────

import uuid
from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient

from src.api.dependencies.admin import require_admin
from src.api.dependencies.auth import require_user
from src.api.dependencies.db import get_db
from src.api.main import app
from src.models.user import User

TEST_ADMIN_ID = "admin_" + uuid.uuid4().hex[:12]


def _make_user(
    user_id: str | None = None,
    tier: str = "free",
    credits: int = 100,
) -> User:
    uid = user_id or "user_" + uuid.uuid4().hex[:12]
    return User(
        id=uid,
        email=f"{uid}@example.com",
        display_name="Test User",
        credits_balance=credits,
        tier=tier,
        referral_code=uid[:8].upper(),
        is_active=True,
    )


def _make_list_mock_db(users: list[User], total: int) -> AsyncMock:
    mock_db = AsyncMock()
    count_result = MagicMock()
    count_result.one.return_value = total
    rows_result = MagicMock()
    rows_result.all.return_value = users
    mock_db.exec = AsyncMock(side_effect=[count_result, rows_result])
    return mock_db


@pytest.fixture
async def admin_list_client():
    user1 = _make_user(tier="free")
    user2 = _make_user(tier="pro")

    async def _override_db():
        yield _make_list_mock_db([user1, user2], total=2)

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": TEST_ADMIN_ID,
        "email": "admin@example.com",
        "tier": "free",
    }
    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_list_users_returns_paginated_response(admin_list_client: AsyncClient) -> None:
    response = await admin_list_client.get("/v1/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert "page" in data
    assert data["total"] == 2
    assert len(data["users"]) == 2
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_users_without_auth_returns_401() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/admin/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_non_admin_returns_403(mocker) -> None:
    mocker.patch(
        "src.api.dependencies.admin.settings",
        type("S", (), {"ADMIN_USER_IDS": "actual_admin_only"})(),
    )
    app.dependency_overrides[require_user] = lambda: {
        "user_id": "not_admin_user",
        "email": "x@x.com",
        "tier": "free",
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/v1/admin/users")
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.pop(require_user, None)


# ── /v1/admin/users/{user_id} (detail) ────────────────────────────────────

from src.models.credit import CreditTransaction


def _make_txn(user_id: str, amount: int = 500, balance_after: int = 500) -> CreditTransaction:
    return CreditTransaction(
        id=1,
        user_id=user_id,
        amount=amount,
        balance_after=balance_after,
        operation="signup_bonus",
    )


def _make_detail_mock_db(
    user: User | None,
    transactions: list[CreditTransaction],
    source_count: int,
) -> AsyncMock:
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=user)

    txn_result = MagicMock()
    txn_result.all.return_value = transactions

    count_result = MagicMock()
    count_result.one.return_value = source_count

    mock_db.exec = AsyncMock(side_effect=[txn_result, count_result])
    return mock_db


@pytest.fixture
async def admin_detail_client():
    user = _make_user(user_id="detail_user_123")
    txn = _make_txn(user_id="detail_user_123")

    async def _override_db():
        yield _make_detail_mock_db(user, [txn], source_count=3)

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": TEST_ADMIN_ID,
        "email": "admin@example.com",
        "tier": "free",
    }
    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_get_user_detail_returns_user_with_transactions(
    admin_detail_client: AsyncClient,
) -> None:
    response = await admin_detail_client.get("/v1/admin/users/detail_user_123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "detail_user_123"
    assert data["source_count"] == 3
    assert len(data["recent_transactions"]) == 1
    assert data["recent_transactions"][0]["operation"] == "signup_bonus"


@pytest.mark.asyncio
async def test_get_user_detail_returns_404_for_missing_user() -> None:
    async def _override_db():
        yield _make_detail_mock_db(user=None, transactions=[], source_count=0)

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": TEST_ADMIN_ID,
        "email": "admin@example.com",
        "tier": "free",
    }
    app.dependency_overrides[get_db] = _override_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/v1/admin/users/nonexistent_user")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_db, None)


# ── /v1/admin/credits/adjust ──────────────────────────────────────────────

def _make_adjust_mock_db(user: User, txn_id: int = 42) -> AsyncMock:
    mock_db = AsyncMock()

    user_result = MagicMock()
    user_result.one_or_none.return_value = user
    mock_db.exec = AsyncMock(return_value=user_result)

    async def _refresh_side_effect(obj: object) -> None:
        obj.id = txn_id  # type: ignore[attr-defined]

    mock_db.refresh = AsyncMock(side_effect=_refresh_side_effect)
    return mock_db


@pytest.fixture
async def admin_adjust_client():
    user = _make_user(user_id="adjust_user_123", credits=100)

    async def _override_db():
        yield _make_adjust_mock_db(user, txn_id=99)

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": TEST_ADMIN_ID,
        "email": "admin@example.com",
        "tier": "free",
    }
    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_adjust_credits_adds_credits(admin_adjust_client: AsyncClient) -> None:
    response = await admin_adjust_client.post(
        "/v1/admin/credits/adjust",
        json={"user_id": "adjust_user_123", "amount": 50, "reason": "manual bonus"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_balance"] == 150  # 100 + 50
    assert data["transaction_id"] == 99


@pytest.mark.asyncio
async def test_adjust_credits_deducts_credits(admin_adjust_client: AsyncClient) -> None:
    response = await admin_adjust_client.post(
        "/v1/admin/credits/adjust",
        json={"user_id": "adjust_user_123", "amount": -30, "reason": "correction"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_balance"] == 70  # 100 - 30


@pytest.mark.asyncio
async def test_adjust_credits_returns_404_for_missing_user() -> None:
    async def _override_db():
        mock_db = AsyncMock()
        not_found = MagicMock()
        not_found.one_or_none.return_value = None
        mock_db.exec = AsyncMock(return_value=not_found)
        yield mock_db

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": TEST_ADMIN_ID,
        "email": "admin@example.com",
        "tier": "free",
    }
    app.dependency_overrides[get_db] = _override_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/v1/admin/credits/adjust",
                json={"user_id": "ghost_user", "amount": 10, "reason": "test"},
            )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_db, None)


# ── /v1/admin/users/{user_id}/toggle-active ───────────────────────────────

def _make_toggle_mock_db(user: User) -> AsyncMock:
    mock_db = AsyncMock()
    user_result = MagicMock()
    user_result.one_or_none.return_value = user
    mock_db.exec = AsyncMock(return_value=user_result)
    return mock_db


@pytest.fixture
async def admin_toggle_client():
    user = _make_user(user_id="toggle_user_123")
    user.is_active = True

    async def _override_db():
        yield _make_toggle_mock_db(user)

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": TEST_ADMIN_ID,
        "email": "admin@example.com",
        "tier": "free",
    }
    app.dependency_overrides[get_db] = _override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_toggle_active_deactivates_user(admin_toggle_client: AsyncClient) -> None:
    response = await admin_toggle_client.post(
        "/v1/admin/users/toggle_user_123/toggle-active",
        json={"active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_toggle_active_returns_404_for_missing_user() -> None:
    async def _override_db():
        mock_db = AsyncMock()
        not_found = MagicMock()
        not_found.one_or_none.return_value = None
        mock_db.exec = AsyncMock(return_value=not_found)
        yield mock_db

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": TEST_ADMIN_ID,
        "email": "admin@example.com",
        "tier": "free",
    }
    app.dependency_overrides[get_db] = _override_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/v1/admin/users/ghost_user/toggle-active",
                json={"active": False},
            )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(require_admin, None)
        app.dependency_overrides.pop(get_db, None)
