from decimal import Decimal

import pytest
from httpx import AsyncClient


async def create_model(
    client: AsyncClient,
    sku: str = "ABC-123",
    filename: str = "model.glb",
    width: str = "120",
    height: str = "80",
    depth: str = "60",
    unit: str = "cm",
):
    return await client.post(
        f"/api/v1/ar/models/{sku}",
        files={
            "file": (
                filename,
                b"test model content",
                "model/gltf-binary",
            ),
        },
        data={
            "width": width,
            "height": height,
            "depth": depth,
            "unit": unit,
        },
    )


@pytest.mark.asyncio
async def test_get_model_when_model_does_not_exist(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/ar/models/ABC-123",
    )

    assert response.status_code == 200

    assert response.json() == {
        "sku": "ABC-123",
        "available": False,
    }


@pytest.mark.asyncio
async def test_create_model(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    response = await create_model(
        client=client,
        sku="ABC-123",
    )

    assert response.status_code == 201

    data = response.json()

    assert data["sku"] == "ABC-123"
    assert data["available"] is True
    assert data["format"] == "glb"
    assert data["file_url"] == "/api/v1/ar/models/ABC-123/file"

    assert Decimal(data["width"]) == Decimal("1.200")
    assert Decimal(data["height"]) == Decimal("0.800")
    assert Decimal(data["depth"]) == Decimal("0.600")
    assert data["unit"] == "m"


@pytest.mark.asyncio
async def test_get_model_when_model_exists(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    create_response = await create_model(
        client=client,
        sku="ABC-123",
    )

    assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/ar/models/ABC-123",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["sku"] == "ABC-123"
    assert data["available"] is True
    assert data["format"] == "glb"
    assert data["file_url"] == "/api/v1/ar/models/ABC-123/file"

    assert Decimal(data["width"]) == Decimal("1.200")
    assert Decimal(data["height"]) == Decimal("0.800")
    assert Decimal(data["depth"]) == Decimal("0.600")
    assert data["unit"] == "m"


@pytest.mark.asyncio
async def test_get_model_by_sku(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    await create_model(
        client=client,
        sku="ABC-123",
    )

    response = await client.get(
        "/api/v1/ar/models/XYZ-456",
    )

    assert response.status_code == 200

    assert response.json() == {
        "sku": "XYZ-456",
        "available": False,
    }


@pytest.mark.asyncio
async def test_get_model_file(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    await create_model(
        client=client,
        sku="ABC-123",
    )

    response = await client.get(
        "/api/v1/ar/models/ABC-123/file",
    )

    assert response.status_code == 200
    assert response.content == b"test model content"


@pytest.mark.asyncio
async def test_get_model_file_when_model_does_not_exist(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/ar/models/ABC-123/file",
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_model(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    await create_model(
        client=client,
        sku="ABC-123",
    )

    response = await client.put(
        "/api/v1/ar/models/ABC-123",
        files={
            "file": (
                "updated.glb",
                b"updated model content",
                "model/gltf-binary",
            ),
        },
        data={
            "width": "250",
            "height": "180",
            "depth": "90",
            "unit": "cm",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["sku"] == "ABC-123"
    assert data["available"] is True
    assert data["format"] == "glb"
    assert Decimal(data["width"]) == Decimal("2.500")
    assert Decimal(data["height"]) == Decimal("1.800")
    assert Decimal(data["depth"]) == Decimal("0.900")
    assert data["unit"] == "m"


@pytest.mark.asyncio
async def test_update_model_when_model_does_not_exist(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    response = await client.put(
        "/api/v1/ar/models/ABC-123",
        files={
            "file": (
                "updated.glb",
                b"updated model content",
                "model/gltf-binary",
            ),
        },
        data={
            "width": "250",
            "height": "180",
            "depth": "90",
            "unit": "cm",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_model_status(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    await create_model(
        client=client,
        sku="ABC-123",
    )

    response = await client.patch(
        "/api/v1/ar/models/ABC-123/status",
        json={
            "status": "not_active",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "sku": "ABC-123",
        "status": "not_active",
    }


@pytest.mark.asyncio
async def test_disabled_model_is_not_available(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    await create_model(
        client=client,
        sku="ABC-123",
    )

    response = await client.patch(
        "/api/v1/ar/models/ABC-123/status",
        json={
            "status": "not_active",
        },
    )

    assert response.status_code == 200

    response = await client.get(
        "/api/v1/ar/models/ABC-123",
    )

    assert response.status_code == 200

    assert response.json() == {
        "sku": "ABC-123",
        "available": False,
    }


@pytest.mark.asyncio
async def test_delete_model(
    client: AsyncClient,
    mock_validate_ar_model_file,
):
    await create_model(
        client=client,
        sku="ABC-123",
    )

    response = await client.delete(
        "/api/v1/ar/models/ABC-123",
    )

    assert response.status_code == 204

    response = await client.get(
        "/api/v1/ar/models/ABC-123",
    )

    assert response.status_code == 200

    assert response.json() == {
        "sku": "ABC-123",
        "available": False,
    }


@pytest.mark.asyncio
async def test_delete_model_when_model_does_not_exist(
    client: AsyncClient,
):
    response = await client.delete(
        "/api/v1/ar/models/ABC-123",
    )

    assert response.status_code == 404