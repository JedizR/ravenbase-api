# tests/unit/services/test_metadoc_service.py
"""Unit tests for MetadocService.

Tests resolve_model() and handle_generate() without hitting real DB/Redis.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.models.user import User


def _make_user(
    tier: str = "free", preferred_model: str = "claude-haiku-4-5-20251001", credits: int = 100
) -> User:
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        tier=tier,
        preferred_model=preferred_model,
        credits_balance=credits,
    )


class TestResolveModel:
    def test_no_alias_uses_user_preferred_model(self):
        from src.services.metadoc_service import MetadocService  # noqa: PLC0415

        user = _make_user(tier="pro", preferred_model="claude-sonnet-4-6")
        model, cost = MetadocService.resolve_model(None, user)
        assert model == "claude-sonnet-4-6"
        assert cost == 45

    def test_haiku_alias_resolves(self):
        from src.services.metadoc_service import MetadocService  # noqa: PLC0415

        user = _make_user()
        model, cost = MetadocService.resolve_model("haiku", user)
        assert model == "claude-haiku-4-5-20251001"
        assert cost == 18

    def test_sonnet_alias_resolves_for_pro(self):
        from src.services.metadoc_service import MetadocService  # noqa: PLC0415

        user = _make_user(tier="pro")
        model, cost = MetadocService.resolve_model("sonnet", user)
        assert model == "claude-sonnet-4-6"
        assert cost == 45

    def test_free_tier_cannot_use_sonnet(self):
        """Free tier user requesting sonnet is silently downgraded to haiku."""
        from src.services.metadoc_service import MetadocService  # noqa: PLC0415

        user = _make_user(tier="free")
        model, cost = MetadocService.resolve_model("sonnet", user)
        assert model == "claude-haiku-4-5-20251001"
        assert cost == 18

    def test_no_alias_no_preferred_falls_back_to_haiku(self):
        from src.services.metadoc_service import MetadocService  # noqa: PLC0415

        user = _make_user(preferred_model="")
        model, cost = MetadocService.resolve_model(None, user)
        assert model == "claude-haiku-4-5-20251001"
        assert cost == 18


class TestHandleGenerate:
    @pytest.mark.asyncio
    async def test_insufficient_credits_raises_402(self):
        """handle_generate raises 402 when user has fewer credits than cost."""
        from src.services.metadoc_service import MetadocService  # noqa: PLC0415

        user = _make_user(credits=5)  # Haiku costs 18
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=user)
        mock_pool = AsyncMock()

        svc = MetadocService()
        with pytest.raises(HTTPException) as exc_info:
            await svc.handle_generate(
                prompt="Tell me about Python",
                profile_id=None,
                model_alias="haiku",
                tenant_id=str(user.id),
                arq_pool=mock_pool,
                db=mock_db,
            )
        assert exc_info.value.status_code == 402
        mock_pool.enqueue_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_sufficient_credits_enqueues_job(self):
        """handle_generate enqueues the job when credits are sufficient."""
        from src.services.metadoc_service import MetadocService  # noqa: PLC0415

        user = _make_user(credits=100)
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=user)

        mock_job = MagicMock()
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_job)

        svc = MetadocService()
        response = await svc.handle_generate(
            prompt="Tell me about Python",
            profile_id=None,
            model_alias="haiku",
            tenant_id=str(user.id),
            arq_pool=mock_pool,
            db=mock_db,
        )

        mock_pool.enqueue_job.assert_called_once()
        assert response.estimated_credits == 18
        assert response.job_id  # non-empty string

    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self):
        """handle_generate raises 404 when tenant_id has no user record."""
        from src.services.metadoc_service import MetadocService  # noqa: PLC0415

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        mock_pool = AsyncMock()

        svc = MetadocService()
        with pytest.raises(HTTPException) as exc_info:
            await svc.handle_generate(
                prompt="test",
                profile_id=None,
                model_alias=None,
                tenant_id=str(uuid.uuid4()),
                arq_pool=mock_pool,
                db=mock_db,
            )
        assert exc_info.value.status_code == 404
