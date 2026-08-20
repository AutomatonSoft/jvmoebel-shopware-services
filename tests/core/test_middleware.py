import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from io import BytesIO

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
        )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Request body too large",
    }


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