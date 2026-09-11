import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from core.middleware import MaxBodySizeMiddleware


@pytest.fixture
def middleware_app_small_limit():
    test_app = FastAPI()

    @test_app.post("/test-upload")
    async def test_upload(request: Request):
        body = await request.body()
        return {"size": len(body)}

    return MaxBodySizeMiddleware(test_app, max_size=100)


@pytest.fixture
async def middleware_client_small(middleware_app_small_limit):
    async with AsyncClient(
        transport=ASGITransport(app=middleware_app_small_limit),
        base_url="http://test",
    ) as client:
        yield client


async def test_request_under_limit(middleware_client_small):
    response = await middleware_client_small.post(
        "/test-upload",
        content=b"x" * 99,
    )
    assert response.status_code == 200
    assert response.json()["size"] == 99


async def test_request_exceeds_limit(middleware_client_small):
    response = await middleware_client_small.post(
        "/test-upload",
        content=b"x" * 101,
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "Request body too large"
