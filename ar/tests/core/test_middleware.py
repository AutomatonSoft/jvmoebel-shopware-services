# tests/core/test_middleware.py
from io import BytesIO

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from core.middleware import MaxBodySizeMiddleware
from core.config import settings
from core.errors_handlers import register_errors_handlers


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
    from main import app_without_middleware

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


@pytest.fixture
def middleware_app_small_limit_with_error_handler():
    """Приложение с глобальным Exception handler, как в проде."""
    test_app = FastAPI()
    register_errors_handlers(test_app)

    @test_app.post("/test-upload")
    async def test_upload(request: Request):
        body = await request.body()
        return {"size": len(body)}

    return MaxBodySizeMiddleware(test_app, max_size=100)


async def _asgi_post_chunked_without_content_length(
    app,
    path: str,
    chunks: list[bytes],
) -> list[dict]:
    messages: list[dict] = []
    state = {"i": 0}

    async def receive():
        index = state["i"]
        if index >= len(chunks):
            return {"type": "http.disconnect"}

        chunk = chunks[index]
        state["i"] += 1
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": state["i"] < len(chunks),
        }

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-type", b"application/octet-stream")],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    await app(scope, receive, send)
    return messages


def _response_starts(messages: list[dict]) -> list[dict]:
    return [
        message
        for message in messages
        if message.get("type") == "http.response.start"
    ]


@pytest.mark.asyncio
class TestMiddlewareChunkedWithoutContentLength:
    """Несколько http.request чанков без Content-Length — ровно один 413."""

    async def test_multiple_chunks_over_limit_sends_single_413(
        self,
        middleware_app_small_limit,
    ):
        messages = await _asgi_post_chunked_without_content_length(
            middleware_app_small_limit,
            "/test-upload",
            [b"x" * 40, b"x" * 40, b"x" * 40],
        )
        starts = _response_starts(messages)

        assert len(starts) == 1
        assert starts[0]["status"] == 413

    async def test_multiple_chunks_with_global_exception_handler_sends_single_413(
        self,
        middleware_app_small_limit_with_error_handler,
    ):
        messages = await _asgi_post_chunked_without_content_length(
            middleware_app_small_limit_with_error_handler,
            "/test-upload",
            [b"x" * 40, b"x" * 40, b"x" * 40],
        )
        starts = _response_starts(messages)

        assert len(starts) == 1
        assert starts[0]["status"] == 413