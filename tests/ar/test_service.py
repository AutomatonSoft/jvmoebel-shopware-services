from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from domains.ar.exceptions import (
    ARModelAlreadyExistsException,
    ARModelNotFoundException,
    InvalidARModelFileException,
)
from domains.ar.models import ARModel
from domains.ar.schemas import (
    SARModelCreate,
    SARModelStatusUpdate,
    SARModelUpdate,
)
from domains.ar.service import ARModelService


@pytest.fixture
def fixtures_dir() -> Path:
    """Путь к директории с фикстурами"""
    return Path(__file__).parent.parent / "fixtures" / "ar"


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


# ============ ТЕСТЫ С РЕАЛЬНЫМ ВАЛИДАТОРОМ ============

@pytest.mark.asyncio
async def test_create_model_with_real_valid_glb(
        db_session: AsyncSession,
        ar_service: ARModelService,
        fixtures_dir,
):
    """Создание модели с реальным валидным GLB файлом"""

    glb_files = list((fixtures_dir / "valid" / "glb").glob("*.glb"))
    if not glb_files:
        pytest.skip("No valid GLB files found in fixtures")

    glb_file = glb_files[0]  # Берем первый валидный GLB

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
        fixtures_dir,
):
    """Создание модели с реальным валидным USDZ файлом"""

    usdz_files = list((fixtures_dir / "valid" / "usdz").glob("*.usdz"))
    if not usdz_files:
        pytest.skip("No valid USDZ files found in fixtures")

    usdz_file = usdz_files[0]  # Берем первый валидный USDZ

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
        fixtures_dir,
):
    """Создание модели с невалидным GLB файлом - rejected"""

    glb_files = list((fixtures_dir / "invalid" / "glb").glob("*.glb"))
    if not glb_files:
        pytest.skip("No invalid GLB files found in fixtures")

    glb_file = glb_files[0]  # Берем первый невалидный GLB

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
        tmp_path,
):
    """Создание модели с текстовым файлом .glb - rejected"""

    fake_glb = tmp_path / "fake.glb"
    fake_glb.write_text("This is not a real GLB file")

    with pytest.raises(InvalidARModelFileException):
        await create_test_model_with_file(
            db_session=db_session,
            service=ar_service,
            file_path=fake_glb,
            sku="TEST-FAKE-GLB",
        )


# ============ ТЕСТЫ С МОКОМ (для тестов, где валидация не важна) ============

# ПРИМЕР: Только этот тест использует мок, остальные - реальный валидатор
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