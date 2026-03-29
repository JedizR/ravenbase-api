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
