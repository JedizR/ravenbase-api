# src/schemas/referral.py
from pydantic import BaseModel


class ApplyReferralRequest(BaseModel):
    referral_code: str


class ReferralResponse(BaseModel):
    referral_code: str
    referral_url: str
    total_referrals: int
    pending_referrals: int
    credits_earned: int
    current_month_count: int
    monthly_cap: int = 50
