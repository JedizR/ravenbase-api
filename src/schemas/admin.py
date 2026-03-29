# src/schemas/admin.py
from datetime import datetime

from pydantic import BaseModel


class AdminUserOut(BaseModel):
    id: str
    email: str
    display_name: str | None
    tier: str
    credits_balance: int
    is_active: bool
    created_at: datetime
    last_active_at: datetime | None

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    users: list[AdminUserOut]
    total: int
    page: int


class AdminTransactionOut(BaseModel):
    id: int
    amount: int
    balance_after: int
    operation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserDetailResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    tier: str
    credits_balance: int
    is_active: bool
    created_at: datetime
    last_active_at: datetime | None
    referral_code: str
    recent_transactions: list[AdminTransactionOut]
    source_count: int


class CreditAdjustRequest(BaseModel):
    user_id: str
    amount: int
    reason: str


class CreditAdjustResponse(BaseModel):
    new_balance: int
    transaction_id: int


class ToggleActiveRequest(BaseModel):
    active: bool


class ToggleActiveResponse(BaseModel):
    is_active: bool


class AdminStatsResponse(BaseModel):
    total_users: int
    active_today: int
    new_today: int
    pro_users: int
    daily_llm_spend_usd: float
    llm_spend_cap_usd: float
    sources_today: int
    metadocs_today: int
