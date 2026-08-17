from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from core.db.postgres import get_async_session

from .dependencies import require_ar_write_access
from .schemas import (
    SARModelAvailableResponse,
    SARModelCreate,
    SARModelStatusUpdate,
    SARModelUnavailableResponse,
    SARModelUpdate,
    SARModelStatusResponse,
)
from .service import ARModelService


router = APIRouter(
    prefix="/ar/models",
    tags=["AR Models"],
)

service = ARModelService()


@router.get(
    "/{sku}",
    response_model=(
        SARModelAvailableResponse
        | SARModelUnavailableResponse
    ),
)
async def get_model(
    sku: str,
    session: AsyncSession = Depends(get_async_session),
):
    model = await service.get_model(
        session=session,
        sku=sku,
    )

    if model is None:
        return SARModelUnavailableResponse(
            sku=sku,
            available=False,
        )

    return SARModelAvailableResponse(
        sku=model.sku,
        available=True,
        format=model.file_format,
        file_url=f"/api/v1/ar/models/{model.sku}/file",
        width=model.width,
        height=model.height,
        depth=model.depth,
        unit="m",
    )


@router.get(
    "/{sku}/file",
)
async def get_model_file(
    sku: str,
    session: AsyncSession = Depends(get_async_session),
):
    file_path = await service.get_model_file(
        session=session,
        sku=sku,
    )

    return FileResponse(
        path=file_path,
    )


@router.post(
    "/{sku}",
    response_model=SARModelAvailableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_model(
    sku: str,
    file: UploadFile = File(...),
    width: Decimal = Form(...),
    height: Decimal = Form(...),
    depth: Decimal = Form(...),
    unit: Literal["m", "cm", "mm"] = Form(...),
    session: AsyncSession = Depends(get_async_session),
    write_access=Depends(require_ar_write_access),
):
    model_in = SARModelCreate(
        width=width,
        height=height,
        depth=depth,
        unit=unit,
    )

    model = await service.create_model(
        session=session,
        sku=sku,
        file=file,
        model_in=model_in,
    )

    return SARModelAvailableResponse(
        sku=model.sku,
        available=True,
        format=model.file_format,
        file_url=f"/api/v1/ar/models/{model.sku}/file",
        width=model.width,
        height=model.height,
        depth=model.depth,
        unit="m",
    )


@router.put(
    "/{sku}",
    response_model=SARModelAvailableResponse,
)
async def update_model(
    sku: str,
    file: UploadFile = File(...),
    width: Decimal = Form(...),
    height: Decimal = Form(...),
    depth: Decimal = Form(...),
    unit: Literal["m", "cm", "mm"] = Form(...),
    session: AsyncSession = Depends(get_async_session),
    write_access=Depends(require_ar_write_access),
):
    model_in = SARModelUpdate(
        width=width,
        height=height,
        depth=depth,
        unit=unit,
    )

    model = await service.update_model(
        session=session,
        sku=sku,
        file=file,
        model_in=model_in,
    )

    return SARModelAvailableResponse(
        sku=model.sku,
        available=True,
        format=model.file_format,
        file_url=f"/api/v1/ar/models/{model.sku}/file",
        width=model.width,
        height=model.height,
        depth=model.depth,
        unit="m",
    )


@router.patch(
    "/{sku}/status",
    response_model=SARModelStatusResponse,
)
async def update_model_status(
    sku: str,
    status_in: SARModelStatusUpdate,
    session: AsyncSession = Depends(get_async_session),
    write_access=Depends(require_ar_write_access),
):
    model = await service.update_status(
        session=session,
        sku=sku,
        status_in=status_in,
    )

    return SARModelStatusResponse(
        sku=model.sku,
        status=model.status,
    )


@router.delete(
    "/{sku}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_model(
    sku: str,
    session: AsyncSession = Depends(get_async_session),
    write_access=Depends(require_ar_write_access),
):
    await service.delete_model(
        session=session,
        sku=sku,
    )