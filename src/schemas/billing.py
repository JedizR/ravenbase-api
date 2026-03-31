# src/schemas/billing.py
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CreateCheckoutSessionRequest(BaseModel):
    tier: Literal["pro", "team"]
    period: Literal["monthly", "annual"]


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class PortalSessionResponse(BaseModel):
    portal_url: str
