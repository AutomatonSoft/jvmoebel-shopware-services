# tests/core/test_middleware.py
from io import BytesIO

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.middleware import MaxBodySizeMiddleware
from app.core.config import settings


@pytest.fixture
def middleware_app():
    """Создает тестовое приложение с middleware."""
    test_app = FastAPI()

    @test_app.post("/test-upload")
    async def test_upload(request: Request):
        body = await request.body()
        return {"size": len(body)}

    wrapped_app = MaxBodySizeMiddleware(
        test_app,
        max_size=settings.ar_max_body_size
    )

    return wrapped_app


@pytest.fixture
def middleware_app_small_limit():
    """Создает тестовое приложение с маленьким лимитом (100 байт)."""
    test_app = FastAPI()

    @test_app.post("/test-upload")
    async def test_upload(request: Request):
        body = await request.body()
        return {"size": len(body)}

    wrapped_app = MaxBodySizeMiddleware(test_app, max_size=100)

    return wrapped_app


@pytest.fixture
async def middleware_client(middleware_app):
    """Клиент для тестов с реальным лимитом."""
    async with AsyncClient(
            transport=ASGITransport(app=middleware_app),
            base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def middleware_client_small(middleware_app_small_limit):
    """Клиент для тестов с маленьким лимитом."""
    async with AsyncClient(
            transport=ASGITransport(app=middleware_app_small_limit),
            base_url="http://test",
    ) as client:
        yield client


# ========== ИЗОЛИРОВАННЫЕ ТЕСТЫ MIDDLEWARE ==========

@pytest.mark.asyncio
class TestMiddlewareWithEnvLimit:
    """Тесты middleware с реальным лимитом."""

    async def test_request_within_limit(self, middleware_client):
        response = await middleware_client.post(
            "/test-upload",
            content=b"x" * 1024,
        )
        assert response.status_code == 200
        assert response.json()["size"] == 1024

    async def test_request_exceeds_limit(self, middleware_client):
        response = await middleware_client.post(
            "/test-upload",
            content=b"x" * (settings.ar_max_body_size + 1),
        )
        assert response.status_code == 413
        assert response.json()["detail"] == "Request body too large"

    async def test_empty_body(self, middleware_client):
        response = await middleware_client.post(
            "/test-upload",
            content=b"",
        )
        assert response.status_code == 200
        assert response.json()["size"] == 0


@pytest.mark.asyncio
class TestMiddlewareWithSmallLimit:
    """Тесты middleware с маленьким лимитом (100 байт)."""

    async def test_request_under_limit(self, middleware_client_small):
        response = await middleware_client_small.post(
            "/test-upload",
            content=b"x" * 99,
        )
        assert response.status_code == 200
        assert response.json()["size"] == 99

    async def test_request_exactly_at_limit(self, middleware_client_small):
        response = await middleware_client_small.post(
            "/test-upload",
            content=b"x" * 100,
        )
        assert response.status_code == 200
        assert response.json()["size"] == 100

    async def test_request_one_byte_over_limit(self, middleware_client_small):
        response = await middleware_client_small.post(
            "/test-upload",
            content=b"x" * 101,
        )
        assert response.status_code == 413
        assert response.json()["detail"] == "Request body too large"


# ========== ИНТЕГРАЦИОННЫЕ ТЕСТЫ MIDDLEWARE С РЕАЛЬНЫМИ ЭНДПОИНТАМИ ==========

@pytest.fixture
def app_with_middleware():
    """Оборачиваем реальное приложение в middleware."""
    from app.main import app_without_middleware

    return MaxBodySizeMiddleware(
        app_without_middleware,
        max_size=settings.ar_max_body_size
    )


@pytest.fixture
async def client_with_middleware(app_with_middleware):
    """Клиент для тестов с middleware на реальных эндпоинтах."""
    async with AsyncClient(
            transport=ASGITransport(app=app_with_middleware),
            base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
class TestMiddlewareWithRealEndpoints:
    """Интеграционные тесты middleware с реальными эндпоинтами."""

    async def test_middleware_rejects_large_file(self, client_with_middleware, auth_headers):
        """Большой файл должен быть отклонен."""
        large_content = b"x" * (settings.ar_max_body_size + 1)

        response = await client_with_middleware.post(
            "/api/v1/ar/models/test-sku",
            files={
                "file": ("test.glb", BytesIO(large_content), "model/gltf-binary"),
                "width": (None, "1.0"),
                "height": (None, "1.0"),
                "depth": (None, "1.0"),
                "unit": (None, "m"),
            },
            headers=auth_headers,
        )

        # Должен быть 413 от middleware
        assert response.status_code == 413
        assert "Request body too large" in response.text

    async def test_middleware_rejects_before_auth(self, client_with_middleware):
        """Middleware должен работать ДО проверки авторизации."""
        large_content = b"x" * (settings.ar_max_body_size + 1)

        response = await client_with_middleware.post(
            "/api/v1/ar/models/test-sku",
            files={
                "file": ("test.glb", BytesIO(large_content), "model/gltf-binary"),
                "width": (None, "1.0"),
                "height": (None, "1.0"),
                "depth": (None, "1.0"),
                "unit": (None, "m"),
            },
            # Без авторизации!
        )

        # Должен быть 413, а не 401
        assert response.status_code == 413
        assert "Request body too large" in response.text

    async def test_middleware_allows_small_file(self, client_with_middleware, auth_headers):
        """Маленький файл должен проходить middleware."""
        small_content = b"x" * 1024  # 1KB

        response = await client_with_middleware.post(
            "/api/v1/ar/models/test-sku-2",
            files={
                "file": ("test.glb", BytesIO(small_content), "model/gltf-binary"),
                "width": (None, "1.0"),
                "height": (None, "1.0"),
                "depth": (None, "1.0"),
                "unit": (None, "m"),
            },
            headers=auth_headers,
        )

        # Не должен быть 413 (может быть 200, 400, 404 - это нормально)
        assert response.status_code != 413