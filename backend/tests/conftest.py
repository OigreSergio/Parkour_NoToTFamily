import os

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True, scope="session")
def _set_test_env() -> None:
    os.environ.setdefault("ENV", "test")
    os.environ.setdefault("JWT_SECRET", "test-secret-not-used-in-prod")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://parkour:parkour@localhost:5432/parkour_test",
    )


@pytest.fixture
async def client():
    from app.main import app

    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
