import os

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

# Applied at import time (not in a fixture) so that test modules importing
# app code at collection time already see a valid configuration. Set (not
# setdefault) so the suite never runs against whatever DB the shell points at.
os.environ["ENV"] = "test"
os.environ["JWT_SECRET"] = "test-secret-not-used-in-prod"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://parkour:parkour@localhost:5432/parkour_test"


@pytest.fixture
async def client():
    from app.main import app

    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
