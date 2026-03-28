# tests/integration/api/test_credits.py
from src.schemas.credits import BalanceResponse, CreditTransactionOut


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
