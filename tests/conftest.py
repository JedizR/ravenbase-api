import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    from src.api.main import app  # noqa: PLC0415

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
