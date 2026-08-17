from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from domains.ar.exceptions import (
    ARModelAlreadyExistsException,
    ARModelNotFoundException,
)
from domains.ar.models import ARModel
from domains.ar.schemas import (
    SARModelCreate,
    SARModelStatusUpdate,
    SARModelUpdate,
)
from domains.ar.service import ARModelService


async def create_test_model(
    db_session: AsyncSession,
    sku: str = "ABC-123",
    filename: str = "model.glb",
    width: str = "120",
    height: str = "80",
    depth: str = "60",
    unit: str = "cm",
) -> ARModel:
    service = ARModelService()

    file = UploadFile(
        file=BytesIO(b"test model content"),
        filename=filename,
    )

    model_in = SARModelCreate(
        width=Decimal(width),
        height=Decimal(height),
        depth=Decimal(depth),
        unit=unit,
    )

    return await service.create_model(
        session=db_session,
        sku=sku,
        file=file,
        model_in=model_in,
    )


@pytest.mark.asyncio
async def test_create_model(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
):
    model = await create_test_model(
        db_session=db_session,
    )

    assert model.id is not None
    assert model.sku == "ABC-123"
    assert model.file_format == "glb"
    assert model.status == "active"

    assert model.width == Decimal("1.200")
    assert model.height == Decimal("0.800")
    assert model.depth == Decimal("0.600")
    assert model.unit == "m"

    assert model.file_path
    assert Path(model.file_path).is_file()


@pytest.mark.parametrize(
    ("unit", "value", "expected"),
    [
        ("m", "2", Decimal("2")),
        ("cm", "200", Decimal("2")),
        ("mm", "2000", Decimal("2")),
    ],
)
@pytest.mark.asyncio
async def test_create_model_converts_dimensions_to_meters(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
    unit: str,
    value: str,
    expected: Decimal,
):
    model = await create_test_model(
        db_session=db_session,
        width=value,
        height=value,
        depth=value,
        unit=unit,
    )

    assert model.width == expected
    assert model.height == expected
    assert model.depth == expected
    assert model.unit == "m"


@pytest.mark.asyncio
async def test_create_model_duplicate_sku(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
):
    await create_test_model(
        db_session=db_session,
        sku="ABC-123",
    )

    with pytest.raises(ARModelAlreadyExistsException):
        await create_test_model(
            db_session=db_session,
            sku="ABC-123",
        )


@pytest.mark.asyncio
async def test_get_model(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
):
    service = ARModelService()

    await create_test_model(
        db_session=db_session,
        sku="ABC-123",
    )

    model = await service.get_model(
        session=db_session,
        sku="ABC-123",
    )

    assert model is not None
    assert model.sku == "ABC-123"
    assert model.status == "active"


@pytest.mark.asyncio
async def test_get_model_when_not_found(
    db_session: AsyncSession,
):
    service = ARModelService()

    model = await service.get_model(
        session=db_session,
        sku="ABC-123",
    )

    assert model is None


@pytest.mark.asyncio
async def test_get_model_when_not_active(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
):
    service = ARModelService()

    await create_test_model(
        db_session=db_session,
        sku="ABC-123",
    )

    await service.update_status(
        session=db_session,
        sku="ABC-123",
        status_in=SARModelStatusUpdate(
            status="not_active",
        ),
    )

    model = await service.get_model(
        session=db_session,
        sku="ABC-123",
    )

    assert model is None


@pytest.mark.asyncio
async def test_update_model(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
):
    service = ARModelService()

    original_model = await create_test_model(
        db_session=db_session,
        sku="ABC-123",
    )

    original_file_path = original_model.file_path

    updated_file = UploadFile(
        file=BytesIO(b"updated model content"),
        filename="updated.glb",
    )

    model = await service.update_model(
        session=db_session,
        sku="ABC-123",
        file=updated_file,
        model_in=SARModelUpdate(
            width=Decimal("2.5"),
            height=Decimal("1.8"),
            depth=Decimal("0.9"),
            unit="m",
        ),
    )

    assert model.id == original_model.id
    assert model.sku == "ABC-123"
    assert model.file_format == "glb"
    assert model.status == "active"

    assert model.width == Decimal("2.500")
    assert model.height == Decimal("1.800")
    assert model.depth == Decimal("0.900")
    assert model.unit == "m"

    assert model.file_path != original_file_path
    assert Path(model.file_path).is_file()
    assert not Path(original_file_path).is_file()


@pytest.mark.asyncio
async def test_update_model_when_not_found(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
):
    service = ARModelService()

    file = UploadFile(
        file=BytesIO(b"updated model content"),
        filename="updated.glb",
    )

    with pytest.raises(ARModelNotFoundException):
        await service.update_model(
            session=db_session,
            sku="ABC-123",
            file=file,
            model_in=SARModelUpdate(
                width=Decimal("2.5"),
                height=Decimal("1.8"),
                depth=Decimal("0.9"),
                unit="m",
            ),
        )


@pytest.mark.asyncio
async def test_update_status(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
):
    service = ARModelService()

    await create_test_model(
        db_session=db_session,
        sku="ABC-123",
    )

    model = await service.update_status(
        session=db_session,
        sku="ABC-123",
        status_in=SARModelStatusUpdate(
            status="not_active",
        ),
    )

    assert model.status == "not_active"


@pytest.mark.asyncio
async def test_update_status_when_not_found(
    db_session: AsyncSession,
):
    service = ARModelService()

    with pytest.raises(ARModelNotFoundException):
        await service.update_status(
            session=db_session,
            sku="ABC-123",
            status_in=SARModelStatusUpdate(
                status="not_active",
            ),
        )


@pytest.mark.asyncio
async def test_delete_model(
    db_session: AsyncSession,
    mock_validate_ar_model_file,
):
    service = ARModelService()

    model = await create_test_model(
        db_session=db_session,
        sku="ABC-123",
    )

    file_path = model.file_path

    await service.delete_model(
        session=db_session,
        sku="ABC-123",
    )

    model = await service.get_model(
        session=db_session,
        sku="ABC-123",
    )

    assert model is None
    assert not await service.storage.exists(
        file_path=file_path,
    )


@pytest.mark.asyncio
async def test_delete_model_when_not_found(
    db_session: AsyncSession,
):
    service = ARModelService()

    with pytest.raises(ARModelNotFoundException):
        await service.delete_model(
            session=db_session,
            sku="ABC-123",
        )