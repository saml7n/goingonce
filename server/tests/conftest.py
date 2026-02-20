import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

import app.database as database
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite://"  # in-memory


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Create a fresh in-memory DB for each test."""
    test_engine = create_async_engine(TEST_DB_URL)
    database.engine = test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
