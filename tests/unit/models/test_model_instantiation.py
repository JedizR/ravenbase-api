# tests/unit/models/test_model_instantiation.py
import uuid

from src.models.user import User


def test_user_default_fields() -> None:
    user = User(email="test@example.com")
    assert user.tier == "free"
    assert user.credits_balance == 200
    assert user.is_active is True
    assert user.preferred_model == "claude-haiku-4-5-20251001"
    assert user.referral_code == ""
    assert user.referral_reward_claimed is False
    assert user.is_archived is False
    assert user.notify_welcome is True
    assert user.notify_low_credits is True
    assert user.notify_ingestion_complete is True
    assert user.notify_account_deletion is True
    assert user.referred_by_user_id is None
    assert isinstance(user.id, uuid.UUID)
