import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import engine
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_engine():
    """Ensure engine connection pool is cleanly disposed after each test."""
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP test client fixture using ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
