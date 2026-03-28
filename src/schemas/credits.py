# src/schemas/credits.py
from datetime import datetime

from pydantic import BaseModel


class CreditTransactionOut(BaseModel):
    id: int
    amount: int
    balance_after: int
    operation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BalanceResponse(BaseModel):
    balance: int
    transactions: list[CreditTransactionOut]
