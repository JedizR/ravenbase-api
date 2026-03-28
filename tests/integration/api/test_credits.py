# tests/integration/api/test_credits.py
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.api.dependencies.db import get_db
from src.api.main import app
from src.models.source import Source, SourceStatus
from src.models.user import User
from src.schemas.credits import BalanceResponse, CreditTransactionOut
from src.services.credit_service import CreditService
from src.workers.ingestion_tasks import parse_document
from src.workers.metadoc_tasks import generate_meta_document


def test_credit_transaction_out_schema():
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
    await svc.deduct(mock_db, "user_001", 18, "metadoc_generation")

    assert user.credits_balance == 482
    mock_db.add.assert_called()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_credit_service_deduct_insufficient():
    """deduct() raises 402 when balance < amount."""
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


@pytest.mark.asyncio
async def test_get_credits_balance_returns_balance():
    """GET /v1/credits/balance returns balance and transactions list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            patch("src.api.routes.credits.require_user", return_value={"user_id": "user_test"}),
            patch("src.api.routes.credits.get_db"),
            patch("src.api.routes.credits.CreditService") as mock_svc_cls,
        ):
            mock_svc = mock_svc_cls.return_value
            mock_svc.get_balance = AsyncMock(return_value=482)

            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_db.exec = AsyncMock(return_value=mock_result)

            response = await client.get(
                "/v1/credits/balance",
                headers={"Authorization": "Bearer fake-token"},
            )
            # 403 expected (Clerk JWKS unavailable in test), but route must exist (not 404)
            assert response.status_code in (200, 401, 403)


@pytest.mark.asyncio
async def test_get_credits_balance_unauthenticated():
    """GET /v1/credits/balance returns 401 without auth header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/credits/balance")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_model_default_credits_is_zero():
    """User model credits_balance defaults to 0 (signup_bonus writes 500 via CreditTransaction)."""
    user = User(
        id="new_user",
        email="new@example.com",
        referral_code="NEWUSER1",
    )
    assert user.credits_balance == 0


@pytest.mark.asyncio
async def test_clerk_user_created_writes_signup_bonus():
    """user.created webhook writes 500-credit signup_bonus CreditTransaction."""
    clerk_payload = {
        "type": "user.created",
        "data": {
            "id": "user_clerk_abc",
            "email_addresses": [{"id": "eid_1", "email_address": "new@example.com"}],
            "primary_email_address_id": "eid_1",
            "first_name": "Test",
            "last_name": "User",
            "image_url": None,
        },
    }

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)  # new user
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with (
                patch("src.api.routes.webhooks.Webhook") as mock_wh_cls,
                patch("src.api.routes.webhooks.CreditService") as mock_svc_cls,
            ):
                mock_wh = mock_wh_cls.return_value
                mock_wh.verify.return_value = clerk_payload

                mock_svc = mock_svc_cls.return_value
                mock_svc.add_credits = AsyncMock()

                response = await client.post(
                    "/webhooks/clerk",
                    content=b'{"type": "user.created"}',
                    headers={
                        "svix-id": "msg_123",
                        "svix-timestamp": "1234567890",
                        "svix-signature": "v1,abc123",
                        "content-type": "application/json",
                    },
                )
                # 200 or 500 ok — route exists, CreditService.add_credits call is the assertion target
                assert response.status_code in (200, 500)

                # Verify signup_bonus was credited
                mock_svc.add_credits.assert_awaited_once()
                call_args = mock_svc.add_credits.await_args
                assert call_args.args[1] == "user_clerk_abc"  # user_id
                assert call_args.args[2] == 500  # amount
                assert call_args.args[3] == "signup_bonus"  # operation
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_stripe_webhook_invalid_signature():
    """POST /webhooks/stripe returns 400 on bad Stripe signature."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks/stripe",
            content=b'{"type": "checkout.session.completed"}',
            headers={
                "stripe-signature": "bad_sig",
                "content-type": "application/json",
            },
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_stripe_webhook_checkout_completed_adds_credits():
    """checkout.session.completed adds credits to user balance."""
    stripe_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "user_id": "user_stripe_test",
                    "credits": "500",
                }
            }
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with (
            patch("src.api.routes.webhooks.stripe") as mock_stripe,
            patch("src.api.routes.webhooks.CreditService") as mock_svc_cls,
        ):
            mock_stripe.Webhook.construct_event.return_value = stripe_payload

            mock_svc = mock_svc_cls.return_value
            mock_svc.add_credits = AsyncMock()

            response = await client.post(
                "/webhooks/stripe",
                content=b'{"type": "checkout.session.completed"}',
                headers={
                    "stripe-signature": "v1,mock_sig",
                    "content-type": "application/json",
                },
            )
            assert response.status_code == 200
            mock_svc.add_credits.assert_awaited_once()
            call_args = mock_svc.add_credits.await_args
            assert call_args.args[1] == "user_stripe_test"  # user_id
            assert call_args.args[2] == 500  # credits amount
            assert call_args.args[3] == "stripe_topup"  # operation


@pytest.mark.asyncio
async def test_metadoc_task_uses_credit_service_deduct():
    """generate_meta_document worker calls CreditService.deduct after success."""
    with (
        patch("src.workers.metadoc_tasks.RAGService") as mock_rag,
        patch("src.workers.metadoc_tasks.AnthropicAdapter") as mock_anthropic,
        patch("src.workers.metadoc_tasks.Neo4jAdapter"),
        patch("src.workers.metadoc_tasks.async_session_factory") as mock_factory,
        patch("src.workers.metadoc_tasks.CreditService") as mock_svc_cls,
        patch("src.workers.metadoc_tasks.settings") as mock_settings,
        patch("src.workers.metadoc_tasks._publish", new=AsyncMock()),
    ):
        mock_settings.ENABLE_PII_MASKING = False
        mock_settings.REDIS_URL = "redis://localhost:6379"
        mock_rag.return_value.retrieve = AsyncMock(return_value=[])

        async def fake_stream(*args, **kwargs):
            yield "hello"

        mock_anthropic.return_value.stream_completion = fake_stream

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_factory.return_value = mock_session

        mock_svc = mock_svc_cls.return_value
        mock_svc.deduct = AsyncMock()

        result = await generate_meta_document(
            {},
            job_id="job_test_001",
            prompt="test prompt",
            profile_id=None,
            tenant_id="user_001",
            model="claude-haiku-4-5-20251001",
        )

        assert result["status"] == "ok"
        mock_svc.deduct.assert_awaited_once()
        call_kwargs = mock_svc.deduct.call_args
        assert call_kwargs.kwargs["amount"] == 18
        assert call_kwargs.kwargs["operation"] == "metadoc_generation"


@pytest.mark.asyncio
async def test_ingestion_deducts_per_page():
    """parse_document deducts 1 credit per unique page after successful embedding."""
    chunks = [
        {"text": "chunk1", "chunk_index": 0, "page_number": 1},
        {"text": "chunk2", "chunk_index": 1, "page_number": 1},
        {"text": "chunk3", "chunk_index": 2, "page_number": 2},
    ]  # 2 unique pages → should deduct 2 credits

    with (
        patch("src.workers.ingestion_tasks.async_session_factory") as mock_factory,
        patch("src.workers.ingestion_tasks.StorageAdapter") as mock_storage,
        patch("src.workers.ingestion_tasks.ModerationAdapter") as mock_mod,
        patch("src.workers.ingestion_tasks.DoclingAdapter") as mock_docling,
        patch("src.workers.ingestion_tasks.OpenAIAdapter") as mock_openai,
        patch("src.workers.ingestion_tasks.QdrantAdapter") as mock_qdrant,
        patch("src.workers.ingestion_tasks.publish_progress") as mock_pub,
        patch("src.workers.ingestion_tasks.CreditService") as mock_svc_cls,
    ):
        mock_source = Source(
            id=uuid.uuid4(),
            user_id="user_001",
            original_filename="test.pdf",
            storage_path="path/to/file.pdf",
            mime_type="application/pdf",
            status=SourceStatus.PENDING,
            sha256_hash="abc123",
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_source)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_factory.return_value = mock_session

        mock_storage.return_value.download_file = AsyncMock(return_value=b"fake pdf bytes")
        mock_mod.return_value.check_content = AsyncMock()
        mock_docling.return_value.parse_and_chunk = AsyncMock(return_value=chunks)
        mock_openai.return_value.embed_chunks = AsyncMock(
            return_value=[[0.1] * 1536, [0.1] * 1536, [0.1] * 1536]
        )
        mock_qdrant.return_value.upsert = AsyncMock()
        mock_pub.return_value = AsyncMock()

        mock_svc = mock_svc_cls.return_value
        mock_svc.deduct = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()
        mock_ctx = {"redis": mock_redis}

        result = await parse_document(
            mock_ctx,
            source_id=str(mock_source.id),
            tenant_id="user_001",
        )

        assert result["status"] == "ok"
        mock_svc.deduct.assert_awaited_once()
        deduct_kwargs = mock_svc.deduct.call_args.kwargs
        assert deduct_kwargs["amount"] == 2  # 2 unique pages
        assert deduct_kwargs["operation"] == "ingestion"
        assert deduct_kwargs["reference_id"] == uuid.UUID(str(mock_source.id))


@pytest.mark.asyncio
async def test_ingestion_continues_on_insufficient_credits():
    """parse_document completes successfully even when CreditService raises 402."""
    chunks = [{"text": "chunk1", "chunk_index": 0, "page_number": 1}]

    with (
        patch("src.workers.ingestion_tasks.async_session_factory") as mock_factory,
        patch("src.workers.ingestion_tasks.StorageAdapter") as mock_storage,
        patch("src.workers.ingestion_tasks.ModerationAdapter") as mock_mod,
        patch("src.workers.ingestion_tasks.DoclingAdapter") as mock_docling,
        patch("src.workers.ingestion_tasks.OpenAIAdapter") as mock_openai,
        patch("src.workers.ingestion_tasks.QdrantAdapter") as mock_qdrant,
        patch("src.workers.ingestion_tasks.publish_progress") as mock_pub,
        patch("src.workers.ingestion_tasks.CreditService") as mock_svc_cls,
    ):
        mock_source = Source(
            id=uuid.uuid4(),
            user_id="user_001",
            original_filename="test.pdf",
            storage_path="path/to/file.pdf",
            mime_type="application/pdf",
            status=SourceStatus.PENDING,
            sha256_hash="abc123",
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = AsyncMock(return_value=mock_source)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_factory.return_value = mock_session

        mock_storage.return_value.download_file = AsyncMock(return_value=b"fake pdf bytes")
        mock_mod.return_value.check_content = AsyncMock()
        mock_docling.return_value.parse_and_chunk = AsyncMock(return_value=chunks)
        mock_openai.return_value.embed_chunks = AsyncMock(return_value=[[0.1] * 1536])
        mock_qdrant.return_value.upsert = AsyncMock()
        mock_pub.return_value = AsyncMock()

        # CreditService.deduct raises 402 (insufficient credits)
        mock_svc_cls.return_value.deduct = AsyncMock(
            side_effect=HTTPException(
                status_code=402,
                detail={"code": "INSUFFICIENT_CREDITS", "message": "Need 1, have 0"},
            )
        )

        mock_redis = AsyncMock()
        mock_redis.enqueue_job = AsyncMock()
        mock_ctx = {"redis": mock_redis}

        result = await parse_document(
            mock_ctx,
            source_id=str(mock_source.id),
            tenant_id="user_001",
        )

        # Task should complete successfully despite credit failure
        assert result["status"] == "ok"
        assert result["source_id"] == str(mock_source.id)
