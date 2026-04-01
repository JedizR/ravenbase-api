import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_clerk_user_deleted_enqueues_cascade_deletion():
    """user.deleted Clerk event enqueues cascade_delete_account ARQ job."""
    payload = {"type": "user.deleted", "data": {"id": "user_to_delete_clerk_001"}}

    mock_arq_pool = AsyncMock()
    mock_arq_pool.enqueue_job = AsyncMock(
        return_value=MagicMock(job_id="gdpr:user_to_delete_clerk_001")
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        app.state.arq_pool = mock_arq_pool
        with patch("src.api.routes.webhooks.Webhook") as mock_wh_cls:
            mock_wh = mock_wh_cls.return_value
            mock_wh.verify.return_value = payload

            response = await client.post(
                "/webhooks/clerk",
                content=json.dumps(payload).encode(),
                headers={
                    "svix-id": "msg_001",
                    "svix-timestamp": "1234567890",
                    "svix-signature": "v1,mock",
                    "content-type": "application/json",
                },
            )
    assert response.status_code == 200
    mock_arq_pool.enqueue_job.assert_awaited_once_with(
        "cascade_delete_account",
        user_id="user_to_delete_clerk_001",
        _job_id="gdpr:user_to_delete_clerk_001",
    )
