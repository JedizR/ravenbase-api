# tests/integration/api/test_credits.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.schemas.credits import BalanceResponse, CreditTransactionOut
from src.services.credit_service import CreditService
from src.models.user import User
from src.models.credit import CreditTransaction


def test_credit_transaction_out_schema():
    from datetime import datetime, UTC
    txn = CreditTransactionOut(
        id=1,
        amount=-18,
        balance_after=482,
        operation="metadoc_generation",
        created_at=datetime.now(UTC),
    )
    assert txn.amount == -18
    assert txn.operation == "metadoc_generation"


def test_balance_response_schema():
    from datetime import datetime, UTC
    resp = BalanceResponse(
        balance=482,
        transactions=[
            CreditTransactionOut(
                id=1,
                amount=-18,
                balance_after=482,
                operation="metadoc_generation",
                created_at=datetime.now(UTC),
            )
        ],
    )
    assert resp.balance == 482
    assert len(resp.transactions) == 1


@pytest.mark.asyncio
async def test_credit_service_deduct_success():
    """deduct() reduces balance and writes CreditTransaction."""
    user = User(
        id="user_001",
        email="test@example.com",
        credits_balance=500,
        referral_code="ABCD1234",
    )

    mock_result = MagicMock()
    mock_result.one.return_value = user

    mock_db = AsyncMock()
    mock_db.exec = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    svc = CreditService()
    result = await svc.deduct(mock_db, "user_001", 18, "metadoc_generation")

    assert user.credits_balance == 482
    mock_db.add.assert_called()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_credit_service_deduct_insufficient():
    """deduct() raises 402 when balance < amount."""
    from fastapi import HTTPException

    user = User(
        id="user_001",
        email="test@example.com",
        credits_balance=5,
        referral_code="ABCD1234",
    )

    mock_result = MagicMock()
    mock_result.one.return_value = user

    mock_db = AsyncMock()
    mock_db.exec = AsyncMock(return_value=mock_result)

    svc = CreditService()
    with pytest.raises(HTTPException) as exc_info:
        await svc.deduct(mock_db, "user_001", 18, "metadoc_generation")

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["code"] == "INSUFFICIENT_CREDITS"


@pytest.mark.asyncio
async def test_credit_service_add_credits():
    """add_credits() increases balance and writes CreditTransaction."""
    user = User(
        id="user_001",
        email="test@example.com",
        credits_balance=0,
        referral_code="ABCD1234",
    )

    mock_result = MagicMock()
    mock_result.one.return_value = user

    mock_db = AsyncMock()
    mock_db.exec = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    svc = CreditService()
    await svc.add_credits(mock_db, "user_001", 500, "signup_bonus")

    assert user.credits_balance == 500
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_credit_service_get_balance():
    """get_balance() returns current user credits_balance."""
    user = User(
        id="user_001",
        email="test@example.com",
        credits_balance=482,
        referral_code="ABCD1234",
    )

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=user)

    svc = CreditService()
    balance = await svc.get_balance(mock_db, "user_001")
    assert balance == 482
