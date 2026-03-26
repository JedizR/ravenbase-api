# tests/unit/workers/test_hello_world.py
import pytest

from src.workers.main import hello_world


@pytest.mark.asyncio
async def test_hello_world_returns_ok():
    result = await hello_world({})
    assert result == {"status": "ok"}
