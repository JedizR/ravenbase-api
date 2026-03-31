# tests/unit/services/test_billing_service.py
"""Unit tests for _get_price_id — pure function, no DB, no Stripe network calls."""

from unittest.mock import patch

import pytest

from src.services.billing_service import _get_price_id


def test_get_price_id_pro_monthly():
    with patch("src.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_PRO_MONTHLY_PRICE_ID = "price_pro_monthly"
        mock_settings.STRIPE_PRO_ANNUAL_PRICE_ID = "price_pro_annual"
        mock_settings.STRIPE_TEAM_MONTHLY_PRICE_ID = "price_team_monthly"
        mock_settings.STRIPE_TEAM_ANNUAL_PRICE_ID = "price_team_annual"
        assert _get_price_id("pro", "monthly") == "price_pro_monthly"


def test_get_price_id_pro_annual():
    with patch("src.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_PRO_MONTHLY_PRICE_ID = "price_pro_monthly"
        mock_settings.STRIPE_PRO_ANNUAL_PRICE_ID = "price_pro_annual"
        mock_settings.STRIPE_TEAM_MONTHLY_PRICE_ID = "price_team_monthly"
        mock_settings.STRIPE_TEAM_ANNUAL_PRICE_ID = "price_team_annual"
        assert _get_price_id("pro", "annual") == "price_pro_annual"


def test_get_price_id_team_monthly():
    with patch("src.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_PRO_MONTHLY_PRICE_ID = "price_pro_monthly"
        mock_settings.STRIPE_PRO_ANNUAL_PRICE_ID = "price_pro_annual"
        mock_settings.STRIPE_TEAM_MONTHLY_PRICE_ID = "price_team_monthly"
        mock_settings.STRIPE_TEAM_ANNUAL_PRICE_ID = "price_team_annual"
        assert _get_price_id("team", "monthly") == "price_team_monthly"


def test_get_price_id_team_annual():
    with patch("src.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_PRO_MONTHLY_PRICE_ID = "price_pro_monthly"
        mock_settings.STRIPE_PRO_ANNUAL_PRICE_ID = "price_pro_annual"
        mock_settings.STRIPE_TEAM_MONTHLY_PRICE_ID = "price_team_monthly"
        mock_settings.STRIPE_TEAM_ANNUAL_PRICE_ID = "price_team_annual"
        assert _get_price_id("team", "annual") == "price_team_annual"


def test_get_price_id_raises_when_empty():
    with patch("src.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_PRO_MONTHLY_PRICE_ID = ""
        mock_settings.STRIPE_PRO_ANNUAL_PRICE_ID = ""
        mock_settings.STRIPE_TEAM_MONTHLY_PRICE_ID = ""
        mock_settings.STRIPE_TEAM_ANNUAL_PRICE_ID = ""
        with pytest.raises(ValueError, match="No Stripe price ID configured"):
            _get_price_id("pro", "monthly")


def test_get_price_id_raises_for_unknown_tier():
    with patch("src.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_PRO_MONTHLY_PRICE_ID = "price_pro_monthly"
        mock_settings.STRIPE_PRO_ANNUAL_PRICE_ID = "price_pro_annual"
        mock_settings.STRIPE_TEAM_MONTHLY_PRICE_ID = "price_team_monthly"
        mock_settings.STRIPE_TEAM_ANNUAL_PRICE_ID = "price_team_annual"
        with pytest.raises(ValueError):
            _get_price_id("enterprise", "monthly")


def test_get_price_id_raises_for_unknown_period():
    with patch("src.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_PRO_MONTHLY_PRICE_ID = "price_pro_monthly"
        mock_settings.STRIPE_PRO_ANNUAL_PRICE_ID = "price_pro_annual"
        mock_settings.STRIPE_TEAM_MONTHLY_PRICE_ID = "price_team_monthly"
        mock_settings.STRIPE_TEAM_ANNUAL_PRICE_ID = "price_team_annual"
        with pytest.raises(ValueError):
            _get_price_id("pro", "quarterly")
