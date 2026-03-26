"""Unit tests for src/workers/utils.py."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.job_status import JobStatus
from src.workers.utils import publish_progress, update_job_status


@pytest.mark.asyncio
async def test_publish_progress_publishes_to_correct_channel():
    """publish_progress writes correct channel and JSON payload."""
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()

    async def fake_from_url(_url):
        return mock_redis

    with patch("src.workers.utils.aioredis.from_url", new=fake_from_url):
        await publish_progress(
            source_id="src-123",
            progress_pct=42,
            message="Parsing...",
            status="active",
        )

    mock_redis.publish.assert_awaited_once()
    channel, raw_payload = mock_redis.publish.call_args[0]
    assert channel == "job:progress:src-123"
    payload = json.loads(raw_payload)
    assert payload == {"progress_pct": 42, "message": "Parsing...", "status": "active"}
    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_progress_closes_redis_on_error():
    """aclose() must be called even when publish raises."""
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(side_effect=RuntimeError("connection lost"))
    mock_redis.aclose = AsyncMock()

    async def fake_from_url(_url):
        return mock_redis

    with patch("src.workers.utils.aioredis.from_url", new=fake_from_url):
        with pytest.raises(RuntimeError, match="connection lost"):
            await publish_progress("src-x", 0, "fail", "active")

    mock_redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_job_status_updates_record():
    """update_job_status mutates the JobStatus record and commits."""
    job = JobStatus(
        id="job-abc",
        user_id="00000000-0000-0000-0000-000000000001",
        job_type="ingestion",
        status="queued",
        progress_pct=0,
    )
    job.created_at = datetime(2020, 1, 1, tzinfo=UTC)
    job.updated_at = datetime(2020, 1, 1, tzinfo=UTC)

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=job)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session)

    with patch("src.workers.utils.async_session_factory", mock_factory):
        await update_job_status("job-abc", "active", 25, "Processing...")

    assert job.status == "active"
    assert job.progress_pct == 25
    assert job.message == "Processing..."
    mock_session.add.assert_called_once_with(job)
    assert job.updated_at > datetime(2020, 1, 1, tzinfo=UTC)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_job_status_noop_when_job_not_found():
    """update_job_status must not commit when the job record does not exist."""
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session)

    with patch("src.workers.utils.async_session_factory", mock_factory):
        await update_job_status("nonexistent", "active", 0, None)

    mock_session.commit.assert_not_awaited()
