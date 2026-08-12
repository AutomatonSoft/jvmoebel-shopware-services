# app/domains/ar/models/router.py

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

from core.db.postgres import get_async_session

from .schemas import (
    SARModelCreate,
    SARModelResponse,
    SARModelUpdate,
)
from .service import ARModelService


router = APIRouter(
    prefix="/ar/models",
    tags=["AR Models"],
)

service = ARModelService()


@router.get(
    "/{sku}",
    response_model=SARModelResponse,
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
        return SARModelResponse(
            sku=sku,
            available=False,
        )

    return SARModelResponse(
        sku=model.sku,
        available=True,
        format=model.file_format,
        file_url=f"/api/v1/ar/models/{model.sku}/file",
        width=model.width,
        height=model.height,
        depth=model.depth,
        unit=model.unit,
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
    response_model=SARModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_model(
    sku: str,
    file: UploadFile = File(...),
    width: float = Form(...),
    height: float = Form(...),
    depth: float = Form(...),
    unit: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
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

    return SARModelResponse(
        sku=model.sku,
        available=True,
        format=model.file_format,
        file_url=f"/api/v1/ar/models/{model.sku}/file",
        width=model.width,
        height=model.height,
        depth=model.depth,
        unit=model.unit,
    )


@router.put(
    "/{sku}",
    response_model=SARModelResponse,
)
async def update_model(
    sku: str,
    file: UploadFile = File(...),
    width: float = Form(...),
    height: float = Form(...),
    depth: float = Form(...),
    unit: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
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

    return SARModelResponse(
        sku=model.sku,
        available=True,
        format=model.file_format,
        file_url=f"/api/v1/ar/models/{model.sku}/file",
        width=model.width,
        height=model.height,
        depth=model.depth,
        unit=model.unit,
    )


@router.delete(
    "/{sku}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_model(
    sku: str,
    session: AsyncSession = Depends(get_async_session),
):
    await service.delete_model(
        session=session,
        sku=sku,
    )