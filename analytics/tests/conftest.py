# tests/conftest.py

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv(".env.test", override=True)

from main import app
from core.config import settings
from core.db.postgres import Base, get_async_session

TEST_ENGINE = create_async_engine(
    settings.db.url,
    echo=False,
    pool_pre_ping=True,
)

TestSessionLocal = async_sessionmaker(
    bind=TEST_ENGINE,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def reset_db():
    async with TEST_ENGINE.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with TEST_ENGINE.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    async def override_get_async_session():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_async_session] = (
        override_get_async_session
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as async_client:
            yield async_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def ingest_auth_headers() -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {settings.analytics_ingest_api_key.get_secret_value()}"
        ),
    }


@pytest.fixture
def read_auth_headers() -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {settings.analytics_read_api_key.get_secret_value()}"
        ),
    }


@pytest.fixture
def invalid_auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer invalid-token",
    }
