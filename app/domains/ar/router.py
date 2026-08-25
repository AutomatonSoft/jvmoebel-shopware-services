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

from core.config import settings
from core.db.postgres import get_async_session

from .dependencies import require_ar_write_access
from .schemas import (
    SARModelAvailableResponse,
    SARModelCreate,
    SARModelStatusUpdate,
    SARModelUnavailableResponse,
    SARModelUpdate,
    SARModelStatusResponse,
    SKU,
)
from .service import ARModelService


router = APIRouter(
    prefix="/ar/models",
    tags=["AR Models"],
)

service = ARModelService()

AR_MODEL_FILE_DESCRIPTION = (
    "AR model file. Supported formats: GLB, USDZ. "
    f"Maximum size is {settings.ar_max_file_size_label}."
)


@router.get(
    "/{sku}",
    response_model=(
        SARModelAvailableResponse
        | SARModelUnavailableResponse
    ),
    responses={
        422: {
            "description": "Invalid SKU format",
        },
    },
)
async def get_model(
    sku: SKU,
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
    responses={
        422: {
            "description": "Invalid SKU format",
        },
        404: {
            "description": "AR model or model file not found",
        },
    },
)
async def get_model_file(
    sku: SKU,
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
    responses={
        422: {
            "description": "Invalid SKU format or non-positive dimensions",
        },
        400: {
            "description": (
                "Unsupported file format, "
                "file too large, invalid file or dimensions"
            ),
        },
        401: {
            "description": "Authentication required or invalid token",
        },
        409: {
            "description": "AR model with this SKU already exists",
        },
        413: {
            "description": "HTTP request body exceeds AR_MAX_BODY_SIZE",
        },
    },
)
async def create_model(
    sku: SKU,
    file: UploadFile = File(
        ...,
        description=AR_MODEL_FILE_DESCRIPTION,
    ),
    width: Decimal = Form(..., gt=0),
    height: Decimal = Form(..., gt=0),
    depth: Decimal = Form(..., gt=0),
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
    responses={
        422: {
            "description": "Invalid SKU format or non-positive dimensions",
        },
        400: {
            "description": (
                "Unsupported file format, "
                "file too large, invalid file or dimensions"
            ),
        },
        401: {
            "description": "Authentication required or invalid token",
        },
        404: {
            "description": "AR model not found",
        },
        413: {
            "description": "HTTP request body exceeds AR_MAX_BODY_SIZE",
        },
    },
)
async def update_model(
    sku: SKU,
    file: UploadFile = File(
        ...,
        description=AR_MODEL_FILE_DESCRIPTION,
    ),
    width: Decimal = Form(..., gt=0),
    height: Decimal = Form(..., gt=0),
    depth: Decimal = Form(..., gt=0),
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
    responses={
        422: {  # Изменено с 400 на 422
            "description": "Invalid SKU format",
        },
        401: {
            "description": "Authentication required or invalid token",
        },
        404: {
            "description": "AR model not found",
        },
    },
)
async def update_model_status(
    status_in: SARModelStatusUpdate,
    sku: SKU,
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
    responses={
        422: {
            "description": "Invalid SKU format",
        },
        401: {
            "description": "Authentication required or invalid token",
        },
        404: {
            "description": "AR model not found",
        },
    },
)
async def delete_model(
    sku: SKU,
    session: AsyncSession = Depends(get_async_session),
    write_access=Depends(require_ar_write_access),
):
    await service.delete_model(
        session=session,
        sku=sku,
    )