from decimal import Decimal
from io import BytesIO
from pathlib import Path
import asyncio

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from domains.ar.exceptions import (
    ARModelAlreadyExistsException,
    ARModelNotFoundException,
    InvalidARModelFileException,
    InvalidSKUException,
)
from domains.ar.models import ARModel
from domains.ar.schemas import (
    SARModelCreate,
    SARModelStatusUpdate,
    SARModelUpdate,
)
from domains.ar.service import ARModelService
from tests.validators.ar_files import dice_glb_bytes, dice_usdz_bytes
from tests.conftest import TestSessionLocal


async def create_test_model_with_file(
        db_session: AsyncSession,
        service: ARModelService,
        file_path: Path,
        sku: str = "ABC-123",
        width: str = "120",
        height: str = "80",
        depth: str = "60",
        unit: str = "cm",
) -> ARModel:
    """Создает тестовую модель с реальным файлом из fixtures"""

    with open(file_path, 'rb') as f:
        file_content = f.read()

    file = UploadFile(
        file=BytesIO(file_content),
        filename=file_path.name,
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


async def create_test_model_with_mock(
        db_session: AsyncSession,
        service: ARModelService,
        mock_validate,
        sku: str = "ABC-123",
        filename: str = "model.glb",
        width: str = "120",
        height: str = "80",
        depth: str = "60",
        unit: str = "cm",
) -> ARModel:
    """Создает тестовую модель с моком (для тестов, где валидация не важна)"""

    mock_validate.return_value = True

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


# =============================================================================
# ТЕСТЫ С РЕАЛЬНЫМ ВАЛИДАТОРОМ (кубик в tests/validators/generated/)
# =============================================================================

@pytest.mark.asyncio
async def test_create_model_with_real_valid_glb(
        db_session: AsyncSession,
        ar_service: ARModelService,
        generated_ar,
):
    # ТЗ service-1: Создание с валидным GLB → создана
    glb_file = generated_ar("valid.glb", dice_glb_bytes())

    model = await create_test_model_with_file(
        db_session=db_session,
        service=ar_service,
        file_path=glb_file,
        sku="TEST-GLB-001",
    )

    assert model.id is not None
    assert model.sku == "TEST-GLB-001"
    assert model.file_format == "glb"
    assert model.status == "active"
    assert Path(model.file_path).is_file()


@pytest.mark.asyncio
async def test_create_model_with_real_valid_usdz(
        db_session: AsyncSession,
        ar_service: ARModelService,
        generated_ar,
):
    # ТЗ service-2: Создание с валидным USDZ → создана
    usdz_file = generated_ar(
        "valid.usdz",
        dice_usdz_bytes(align=True),
    )

    model = await create_test_model_with_file(
        db_session=db_session,
        service=ar_service,
        file_path=usdz_file,
        sku="TEST-USDZ-001",
    )

    assert model.id is not None
    assert model.sku == "TEST-USDZ-001"
    assert model.file_format == "usdz"
    assert model.status == "active"
    assert Path(model.file_path).is_file()


@pytest.mark.asyncio
async def test_create_model_with_invalid_glb_rejected(
        db_session: AsyncSession,
        ar_service: ARModelService,
        generated_ar,
):
    # ТЗ service-3: Создание с невалидным GLB → Exception
    glb_file = generated_ar(
        "invalid.glb",
        dice_glb_bytes(version=1),
    )

    with pytest.raises(InvalidARModelFileException):
        await create_test_model_with_file(
            db_session=db_session,
            service=ar_service,
            file_path=glb_file,
            sku="TEST-INVALID-GLB",
        )


@pytest.mark.asyncio
async def test_create_model_with_fake_text_glb_rejected(
        db_session: AsyncSession,
        ar_service: ARModelService,
        generated_ar,
):
    # ТЗ service-3: Создание с невалидным GLB → Exception
    fake_glb = generated_ar(
        "fake.glb",
        b"This is not a real GLB file",
    )

    with pytest.raises(InvalidARModelFileException):
        await create_test_model_with_file(
            db_session=db_session,
            service=ar_service,
            file_path=fake_glb,
            sku="TEST-FAKE-GLB",
        )


@pytest.mark.asyncio
async def test_update_model_with_valid_glb(
        db_session: AsyncSession,
        ar_service: ARModelService,
        generated_ar,
):
    # ТЗ service-4: Обновление с валидным GLB → обновлена
    create_file = generated_ar("create.glb", dice_glb_bytes())
    original = await create_test_model_with_file(
        db_session=db_session,
        service=ar_service,
        file_path=create_file,
        sku="TEST-UPD-001",
    )
    original_path = original.file_path

    update_file = generated_ar("updated.glb", dice_glb_bytes())

    updated = await ar_service.update_model(
        session=db_session,
        sku="TEST-UPD-001",
        file=UploadFile(
            file=BytesIO(update_file.read_bytes()),
            filename="updated.glb",
        ),
        model_in=SARModelUpdate(
            width=Decimal("2.5"),
            height=Decimal("1.8"),
            depth=Decimal("0.9"),
            unit="m",
        ),
    )

    assert updated.id == original.id
    assert updated.sku == "TEST-UPD-001"
    assert updated.file_format == "glb"
    assert updated.width == Decimal("2.500")
    assert Path(updated.file_path).is_file()
    assert updated.file_path != original_path


@pytest.mark.asyncio
async def test_update_model_with_invalid_glb_rejected(
        db_session: AsyncSession,
        ar_service: ARModelService,
        generated_ar,
):
    # ТЗ service-5: Обновление с невалидным GLB → Exception
    create_file = generated_ar("create.glb", dice_glb_bytes())
    await create_test_model_with_file(
        db_session=db_session,
        service=ar_service,
        file_path=create_file,
        sku="TEST-UPD-002",
    )

    invalid_file = generated_ar(
        "invalid.glb",
        dice_glb_bytes(declared_length=100),
    )

    with pytest.raises(InvalidARModelFileException):
        await ar_service.update_model(
            session=db_session,
            sku="TEST-UPD-002",
            file=UploadFile(
                file=BytesIO(invalid_file.read_bytes()),
                filename="invalid.glb",
            ),
            model_in=SARModelUpdate(
                width=Decimal("2.5"),
                height=Decimal("1.8"),
                depth=Decimal("0.9"),
                unit="m",
            ),
        )


# =============================================================================
# ТЕСТЫ С МОКОМ (валидация НЕ проверяется, используется mock)
# =============================================================================

@pytest.mark.asyncio
async def test_create_model_converts_dimensions_to_meters(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Проверка конвертации размеров - используем мок, т.к. валидация не важна"""

    model = await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
        width="2",
        height="2",
        depth="2",
        unit="m",
    )

    assert model.width == Decimal("2")
    assert model.height == Decimal("2")
    assert model.depth == Decimal("2")
    assert model.unit == "m"


@pytest.mark.parametrize(
    ("unit", "value", "expected"),
    [
        ("m", "2", Decimal("2")),
        ("cm", "200", Decimal("2")),
        ("mm", "2000", Decimal("2")),
    ],
)
@pytest.mark.asyncio
async def test_create_model_converts_dimensions_to_meters_parametrized(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
        unit: str,
        value: str,
        expected: Decimal,
):
    """Проверка конвертации разных единиц измерения - используем мок"""

    model = await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
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
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Проверка дублирования SKU - используем мок"""

    await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
        sku="ABC-123",
    )

    with pytest.raises(ARModelAlreadyExistsException):
        await create_test_model_with_mock(
            db_session=db_session,
            service=ar_service,
            mock_validate=mock_validate_ar_model_file,
            sku="ABC-123",
        )


@pytest.mark.asyncio
async def test_get_model(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Получение модели - используем мок"""

    await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
        sku="ABC-123",
    )

    model = await ar_service.get_model(
        session=db_session,
        sku="ABC-123",
    )

    assert model is not None
    assert model.sku == "ABC-123"
    assert model.status == "active"


@pytest.mark.asyncio
async def test_get_model_when_not_found(
        db_session: AsyncSession,
        ar_service: ARModelService,
):
    """Получение несуществующей модели"""

    model = await ar_service.get_model(
        session=db_session,
        sku="ABC-123",
    )

    assert model is None


@pytest.mark.asyncio
async def test_get_model_when_not_active(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Получение неактивной модели - используем мок"""

    await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
        sku="ABC-123",
    )

    await ar_service.update_status(
        session=db_session,
        sku="ABC-123",
        status_in=SARModelStatusUpdate(
            status="not_active",
        ),
    )

    model = await ar_service.get_model(
        session=db_session,
        sku="ABC-123",
    )

    assert model is None


@pytest.mark.asyncio
async def test_update_model(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Обновление модели - используем мок"""

    original_model = await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
        sku="ABC-123",
    )

    original_file_path = original_model.file_path

    updated_file = UploadFile(
        file=BytesIO(b"updated model content"),
        filename="updated.glb",
    )

    mock_validate_ar_model_file.return_value = True

    model = await ar_service.update_model(
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
async def test_concurrent_updates_leave_only_current_file(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Два параллельных PUT не должны оставлять orphan-файлы."""

    original_model = await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
        sku="ABC-123",
    )
    original_file_path = original_model.file_path

    async def update_with_new_session(content: bytes) -> None:
        async with TestSessionLocal() as session:
            await ar_service.update_model(
                session=session,
                sku="ABC-123",
                file=UploadFile(
                    file=BytesIO(content),
                    filename="updated.glb",
                ),
                model_in=SARModelUpdate(
                    width=Decimal("2.5"),
                    height=Decimal("1.8"),
                    depth=Decimal("0.9"),
                    unit="m",
                ),
            )

    await asyncio.gather(
        update_with_new_session(b"first concurrent update"),
        update_with_new_session(b"second concurrent update"),
    )

    async with TestSessionLocal() as session:
        current = await ar_service.repository.get_model_by_sku(
            session=session,
            sku="ABC-123",
        )

    assert current is not None
    assert Path(current.file_path).is_file()
    assert not Path(original_file_path).is_file()

    leftover_files = {
        path.resolve()
        for path in Path(current.file_path).parent.iterdir()
        if path.is_file()
    }
    assert leftover_files == {Path(current.file_path).resolve()}


@pytest.mark.asyncio
async def test_update_model_when_not_found(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Обновление несуществующей модели - используем мок"""

    file = UploadFile(
        file=BytesIO(b"updated model content"),
        filename="updated.glb",
    )

    mock_validate_ar_model_file.return_value = True

    with pytest.raises(ARModelNotFoundException):
        await ar_service.update_model(
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
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Обновление статуса - используем мок"""

    await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
        sku="ABC-123",
    )

    model = await ar_service.update_status(
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
        ar_service: ARModelService,
):
    """Обновление статуса несуществующей модели"""

    with pytest.raises(ARModelNotFoundException):
        await ar_service.update_status(
            session=db_session,
            sku="ABC-123",
            status_in=SARModelStatusUpdate(
                status="not_active",
            ),
        )


@pytest.mark.asyncio
async def test_delete_model(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Удаление модели - используем мок"""

    model = await create_test_model_with_mock(
        db_session=db_session,
        service=ar_service,
        mock_validate=mock_validate_ar_model_file,
        sku="ABC-123",
    )

    file_path = model.file_path

    await ar_service.delete_model(
        session=db_session,
        sku="ABC-123",
    )

    model = await ar_service.get_model(
        session=db_session,
        sku="ABC-123",
    )

    assert model is None
    assert not await ar_service.storage.exists(
        file_path=file_path,
    )


@pytest.mark.asyncio
async def test_delete_model_when_not_found(
        db_session: AsyncSession,
        ar_service: ARModelService,
):
    """Удаление несуществующей модели"""

    with pytest.raises(ARModelNotFoundException):
        await ar_service.delete_model(
            session=db_session,
            sku="ABC-123",
        )


# =============================================================================
# ТЕСТЫ SKU ВАЛИДАЦИИ
# =============================================================================

@pytest.mark.asyncio
async def test_create_model_with_invalid_sku_raises_error(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Создание модели с невалидным SKU должно вызывать InvalidSKUException"""

    mock_validate_ar_model_file.return_value = True

    invalid_skus = [
        "-invalid-sku",      # начинается с -
        "_invalid_sku",      # начинается с _
        "../etc/passwd",     # path traversal
        "sku/with/slash",    # содержит /
        "sku\\with\\backslash",  # содержит \
        "with..dots",        # содержит ..
        "a" * 100,           # слишком длинный
        "with\0null",        # содержит null byte
        "with space",        # содержит пробел
    ]

    for invalid_sku in invalid_skus:
        file = UploadFile(
            file=BytesIO(b"test model content"),
            filename="model.glb",
        )

        model_in = SARModelCreate(
            width=Decimal("120"),
            height=Decimal("80"),
            depth=Decimal("60"),
            unit="cm",
        )

        with pytest.raises(InvalidSKUException) as exc_info:
            await ar_service.create_model(
                session=db_session,
                sku=invalid_sku,
                file=file,
                model_in=model_in,
            )

        assert "Invalid SKU format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_model_with_invalid_sku_raises_error(
        db_session: AsyncSession,
        ar_service: ARModelService,
):
    """Получение модели с невалидным SKU должно вызывать InvalidSKUException"""

    invalid_skus = [
        "-invalid",
        "_invalid",
        "../etc/passwd",
        "with/slash",
        "with\\backslash",
        "with..dots",
    ]

    for invalid_sku in invalid_skus:
        with pytest.raises(InvalidSKUException):
            await ar_service.get_model(
                session=db_session,
                sku=invalid_sku,
            )


@pytest.mark.asyncio
async def test_get_model_file_with_invalid_sku_raises_error(
        db_session: AsyncSession,
        ar_service: ARModelService,
):
    """Получение файла модели с невалидным SKU должно вызывать InvalidSKUException"""

    with pytest.raises(InvalidSKUException):
        await ar_service.get_model_file(
            session=db_session,
            sku="../etc/passwd",
        )


@pytest.mark.asyncio
async def test_update_model_with_invalid_sku_raises_error(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Обновление модели с невалидным SKU должно вызывать InvalidSKUException"""

    mock_validate_ar_model_file.return_value = True

    file = UploadFile(
        file=BytesIO(b"updated model content"),
        filename="updated.glb",
    )

    model_in = SARModelUpdate(
        width=Decimal("2.5"),
        height=Decimal("1.8"),
        depth=Decimal("0.9"),
        unit="m",
    )

    with pytest.raises(InvalidSKUException):
        await ar_service.update_model(
            session=db_session,
            sku="../etc/passwd",
            file=file,
            model_in=model_in,
        )


@pytest.mark.asyncio
async def test_update_status_with_invalid_sku_raises_error(
        db_session: AsyncSession,
        ar_service: ARModelService,
):
    """Обновление статуса с невалидным SKU должно вызывать InvalidSKUException"""

    status_in = SARModelStatusUpdate(status="not_active")

    with pytest.raises(InvalidSKUException):
        await ar_service.update_status(
            session=db_session,
            sku="../etc/passwd",
            status_in=status_in,
        )


@pytest.mark.asyncio
async def test_delete_model_with_invalid_sku_raises_error(
        db_session: AsyncSession,
        ar_service: ARModelService,
):
    """Удаление модели с невалидным SKU должно вызывать InvalidSKUException"""

    with pytest.raises(InvalidSKUException):
        await ar_service.delete_model(
            session=db_session,
            sku="../etc/passwd",
        )


@pytest.mark.asyncio
async def test_create_model_with_sku_max_length_valid(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Создание модели с SKU максимальной длины (64 символа) должно работать"""

    mock_validate_ar_model_file.return_value = True

    sku_64 = "a" * 64  # ровно 64 символа

    file = UploadFile(
        file=BytesIO(b"test model content"),
        filename="model.glb",
    )

    model_in = SARModelCreate(
        width=Decimal("120"),
        height=Decimal("80"),
        depth=Decimal("60"),
        unit="cm",
    )

    model = await ar_service.create_model(
        session=db_session,
        sku=sku_64,
        file=file,
        model_in=model_in,
    )

    assert model.sku == sku_64


@pytest.mark.asyncio
async def test_create_model_with_sku_too_long_raises_error(
        db_session: AsyncSession,
        ar_service: ARModelService,
        mock_validate_ar_model_file,
):
    """Создание модели с SKU длиннее 64 символов должно вызывать InvalidSKUException"""

    mock_validate_ar_model_file.return_value = True

    sku_65 = "a" * 65  # 65 символов

    file = UploadFile(
        file=BytesIO(b"test model content"),
        filename="model.glb",
    )

    model_in = SARModelCreate(
        width=Decimal("120"),
        height=Decimal("80"),
        depth=Decimal("60"),
        unit="cm",
    )

    with pytest.raises(InvalidSKUException):
        await ar_service.create_model(
            session=db_session,
            sku=sku_65,
            file=file,
            model_in=model_in,
        )