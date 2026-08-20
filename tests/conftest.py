# tests/conftest.py
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv(".env.test", override=True)


from app.main import app_without_middleware as app
from core.config import settings
from core.db.postgres import Base, get_async_session
from domains.ar.router import service
from domains.ar.service import ARModelService

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
def auth_headers():
    return {
        "Authorization": (
            f"Bearer {settings.ar_write_api_key.get_secret_value()}"
        ),
    }


@pytest.fixture
def invalid_auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer invalid-token",
    }


@pytest.fixture(autouse=True)
def storage(tmp_path: Path):
    # base_path = tmp_path / "ar_models" # dev хранилище
    base_path = tmp_path / "ar_models_test"  # test хранилище (сразу удаляет сохраненные файлы)
    # base_path = Path("app/storage/ar_models_test") # test хранилище (сохраняет все файлы)
    base_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    service.storage.base_path = base_path

    yield service.storage


@pytest.fixture
def ar_service(tmp_path: Path):
    ar_service = ARModelService()

    base_path = tmp_path / "ar_models"

    base_path.mkdir(
        parents=True,
        exist_ok=True
    )

    ar_service.storage.base_path = base_path

    return ar_service


@pytest.fixture
def mock_validate_ar_model_file(monkeypatch):
    """Мок для валидатора AR моделей."""

    def mock_validate(*args, **kwargs) -> bool:
        """Всегда возвращает True — валидация всегда проходит."""
        return True

    monkeypatch.setattr(
        "domains.ar.validators.factory.ValidatorFactory.validate",
        mock_validate,
    )

    return mock_validate
