# tests/conftest.py

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

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

from main import app_without_middleware as app
from core.config import settings
from core.db.postgres import Base, get_async_session
import core.db.models  # noqa: F401 — register ORM models
from domains.ingestion.service import persist_validated_event

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "contracts"
INGEST_ORIGIN = "http://test"

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


@pytest_asyncio.fixture(autouse=True)
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
def ingest_headers(ingest_auth_headers: dict[str, str]) -> dict[str, str]:
    return {
        **ingest_auth_headers,
        "Origin": INGEST_ORIGIN,
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


@pytest.fixture
def session_started_event() -> dict:
    path = (
        CONTRACTS_DIR
        / "http"
        / "examples"
        / "valid"
        / "session-started.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def unique_event():
    def _unique(event: dict) -> dict:
        copied = deepcopy(event)
        copied["event_id"] = str(uuid4())
        return copied

    return _unique


@pytest_asyncio.fixture
async def persist_event(db_session):
    async def _run(body: dict):
        async with db_session.begin():
            return await persist_validated_event(db_session, body)

    return _run


@pytest.fixture
def load_shopware_event(unique_event):
    def _load(stem: str) -> dict:
        path = (
            CONTRACTS_DIR
            / "rabbitmq"
            / "examples"
            / "valid"
            / f"{stem}.json"
        )
        return unique_event(json.loads(path.read_text(encoding="utf-8")))

    return _load


@pytest.fixture
def shopware_order_paid_event() -> dict:
    path = (
        CONTRACTS_DIR
        / "rabbitmq"
        / "examples"
        / "valid"
        / "order-paid.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))
