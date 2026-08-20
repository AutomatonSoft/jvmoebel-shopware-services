from io import BytesIO

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.middleware import MaxBodySizeMiddleware


@pytest.fixture
def app_with_small_limit() -> FastAPI:
    """Создает приложение с маленьким лимитом для тестов."""

    app = FastAPI()

    app.add_middleware(
        MaxBodySizeMiddleware,
        max_size=100,
    )

    @app.post("/test-upload")
    async def test_upload(request: Request):
        body = await request.body()

        return {
            "size": len(body),
        }

    return app


@pytest.mark.asyncio
async def test_request_within_limit(
    app_with_small_limit: FastAPI,
):
    """Запрос меньше лимита должен успешно проходить."""

    async with AsyncClient(
        transport=ASGITransport(app=app_with_small_limit),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/test-upload",
            content=b"x" * 99,
        )

    assert response.status_code == 200
    assert response.json()["size"] == 99


@pytest.mark.asyncio
async def test_request_exactly_at_limit(
    app_with_small_limit: FastAPI,
):
    """Запрос ровно размером с лимит должен успешно проходить."""

    async with AsyncClient(
        transport=ASGITransport(app=app_with_small_limit),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/test-upload",
            content=b"x" * 100,
        )

    assert response.status_code == 200
    assert response.json()["size"] == 100


@pytest.mark.asyncio
async def test_request_exceeds_limit(
    app_with_small_limit: FastAPI,
):
    """Запрос больше лимита должен возвращать 413."""

    async with AsyncClient(
        transport=ASGITransport(app=app_with_small_limit),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/test-upload",
            content=b"x" * 101,
        )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Request body too large",
    }


@pytest.mark.asyncio
async def test_content_length_exceeds_limit(
    app_with_small_limit: FastAPI,
):
    """
    Content-Length больше лимита должен быть отклонен
    до запуска endpoint.
    """

    async with AsyncClient(
        transport=ASGITransport(app=app_with_small_limit),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/test-upload",
            content=b"x" * 150,
            headers={
                "Content-Length": "150",
            },
        )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Request body too large",
    }


@pytest.mark.asyncio
async def test_request_without_content_length_exceeds_limit(
    app_with_small_limit: FastAPI,
):
    """
    Запрос без Content-Length должен быть отклонен,
    когда фактический размер body превышает лимит.
    """

    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0",
            "spec_version": "2.4",
        },
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/test-upload",
        "raw_path": b"/test-upload",
        "query_string": b"",
        "headers": [
            (b"host", b"test"),
            (b"content-type", b"application/octet-stream"),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }

    messages = [
        {
            "type": "http.request",
            "body": b"x" * 60,
            "more_body": True,
        },
        {
            "type": "http.request",
            "body": b"x" * 41,
            "more_body": False,
        },
    ]

    sent_messages = []

    async def receive():
        return messages.pop(0)

    async def send(message):
        sent_messages.append(message)

    await app_with_small_limit(
        scope,
        receive,
        send,
    )

    response_start = sent_messages[0]
    response_body = sent_messages[1]

    assert response_start["status"] == 413
    assert response_body["body"] == (
        b'{"detail":"Request body too large"}'
    )


@pytest.mark.asyncio
async def test_empty_body(
    app_with_small_limit: FastAPI,
):
    """Пустой body должен успешно проходить."""

    async with AsyncClient(
        transport=ASGITransport(app=app_with_small_limit),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/test-upload",
            content=b"",
        )

    assert response.status_code == 200
    assert response.json()["size"] == 0


# =============================================


@pytest.mark.asyncio
async def test_multipart_file_exceeds_limit(
    app_with_small_limit: FastAPI,
):
    """
    Multipart upload, размер которого превышает лимит,
    должен быть отклонен middleware.
    """

    file_content = b"x" * 101

    async with AsyncClient(
        transport=ASGITransport(app=app_with_small_limit),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/test-upload",
            files={
                "file": (
                    "model.glb",
                    BytesIO(file_content),
                    "model/gltf-binary",
                ),
            },
        )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Request body too large",
    }


@pytest.mark.asyncio
async def test_multipart_file_within_limit():
    """
    Multipart upload, размер всего HTTP body которого
    находится в пределах лимита, должен успешно проходить.
    """

    app = FastAPI()

    app.add_middleware(
        MaxBodySizeMiddleware,
        max_size=1000,
    )

    @app.post("/test-upload")
    async def test_upload():
        return {"status": "ok"}

    file_content = b"x"

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/test-upload",
            files={
                "file": (
                    "model.glb",
                    BytesIO(file_content),
                    "model/gltf-binary",
                ),
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }