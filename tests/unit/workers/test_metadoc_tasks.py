# tests/unit/workers/test_metadoc_tasks.py
"""Unit tests for generate_meta_document ARQ task.

All external I/O (RAGService, AnthropicAdapter, DB, Redis, Neo4j) is mocked.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.config import settings as _settings
from src.schemas.rag import RetrievedChunk
from src.workers.metadoc_tasks import generate_meta_document


def _make_chunk(content: str = "test content") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=str(uuid.uuid4()),
        content=content,
        source_id=uuid.uuid4(),
        memory_id=uuid.uuid4(),
        final_score=0.9,
        semantic_score=0.8,
        recency_weight=0.7,
    )


@pytest.mark.asyncio
async def test_generate_meta_document_publishes_done_event(mocker):
    """Successful generation publishes a 'done' event to Redis."""
    mock_chunks = [_make_chunk("Python is great.")]

    mocker.patch(
        "src.workers.metadoc_tasks.RAGService.retrieve",
        new=AsyncMock(return_value=mock_chunks),
    )
    mocker.patch(
        "src.workers.metadoc_tasks.AnthropicAdapter.stream_completion",
        return_value=_async_gen(["Python", " is", " great."]),
    )
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mocker.patch(
        "src.workers.metadoc_tasks.aioredis.from_url",
        return_value=mock_redis,
    )
    mocker.patch(
        "src.workers.metadoc_tasks.async_session_factory",
        return_value=_fake_session_ctx(),
    )
    mocker.patch(
        "src.workers.metadoc_tasks.Neo4jAdapter.write_contains_edges",
        new=AsyncMock(),
    )
    mocker.patch.object(_settings, "ENABLE_PII_MASKING", False)

    ctx: dict = {}
    result = await generate_meta_document(
        ctx,
        job_id="job-001",
        prompt="Tell me about Python",
        profile_id=None,
        tenant_id=str(uuid.uuid4()),
        model="claude-haiku-4-5-20251001",
    )

    assert result["status"] == "ok"
    # Verify 'done' event was published
    published_calls = mock_redis.publish.call_args_list
    channel_calls = [str(c[0][0]) for c in published_calls]
    assert any("metadoc:stream:job-001" in ch for ch in channel_calls)
    payloads = [json.loads(c[0][1]) for c in published_calls]
    done_events = [p for p in payloads if p.get("type") == "done"]
    assert len(done_events) == 1
    assert "doc_id" in done_events[0]
    assert done_events[0]["credits_consumed"] == 18


@pytest.mark.asyncio
async def test_generate_meta_document_publishes_error_on_timeout(mocker):
    """Timeout during streaming publishes an error event and returns status=timeout."""
    mocker.patch(
        "src.workers.metadoc_tasks.RAGService.retrieve",
        new=AsyncMock(return_value=[_make_chunk()]),
    )

    async def _timeout_gen(*args, **kwargs):
        raise TimeoutError("timed out")
        yield  # make it a generator

    mocker.patch(
        "src.workers.metadoc_tasks.AnthropicAdapter.stream_completion",
        return_value=_timeout_gen(),
    )
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mocker.patch("src.workers.metadoc_tasks.aioredis.from_url", return_value=mock_redis)
    mocker.patch.object(_settings, "ENABLE_PII_MASKING", False)

    ctx: dict = {}
    result = await generate_meta_document(
        ctx,
        job_id="job-timeout",
        prompt="test",
        profile_id=None,
        tenant_id=str(uuid.uuid4()),
        model="claude-haiku-4-5-20251001",
    )

    assert result["status"] in ("timeout", "error")
    payloads = [json.loads(c[0][1]) for c in mock_redis.publish.call_args_list]
    error_events = [p for p in payloads if p.get("type") == "error"]
    assert len(error_events) >= 1


@pytest.mark.asyncio
async def test_generate_meta_document_masks_pii_when_enabled(mocker):
    """PII masking is called on each chunk when ENABLE_PII_MASKING=True."""
    chunk = _make_chunk("John Smith wrote this.")
    mocker.patch(
        "src.workers.metadoc_tasks.RAGService.retrieve",
        new=AsyncMock(return_value=[chunk]),
    )
    mock_mask = MagicMock(return_value=("Entity_000 wrote this.", {"John Smith": "Entity_000"}))
    mocker.patch(
        "src.workers.metadoc_tasks.PresidioAdapter.mask_for_llm",
        mock_mask,
    )
    mocker.patch(
        "src.workers.metadoc_tasks.AnthropicAdapter.stream_completion",
        return_value=_async_gen(["done"]),
    )
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mocker.patch("src.workers.metadoc_tasks.aioredis.from_url", return_value=mock_redis)
    mocker.patch(
        "src.workers.metadoc_tasks.async_session_factory",
        return_value=_fake_session_ctx(),
    )
    mocker.patch(
        "src.workers.metadoc_tasks.Neo4jAdapter.write_contains_edges",
        new=AsyncMock(),
    )
    mocker.patch.object(_settings, "ENABLE_PII_MASKING", True)

    ctx: dict = {}
    await generate_meta_document(
        ctx,
        job_id="job-pii",
        prompt="Who wrote this?",
        profile_id=None,
        tenant_id=str(uuid.uuid4()),
        model="claude-haiku-4-5-20251001",
    )

    mock_mask.assert_called_once_with("John Smith wrote this.")


# --------------- helpers ---------------


async def _async_gen(tokens):
    for t in tokens:
        yield t


def _fake_session_ctx():
    """Returns a factory that acts as an async context manager yielding a mock session."""
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=_fake_user())
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    class _Ctx:
        def __call__(self):
            return self

        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, *args):
            return False

    return _Ctx()


def _fake_user():
    from src.models.user import User  # noqa: PLC0415
    return User(
        id=uuid.uuid4(),
        email="x@example.com",
        credits_balance=100,
        tier="free",
    )
