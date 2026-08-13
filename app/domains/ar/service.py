# app/domains/ar/service.py

import logging
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import (
    ARModelAlreadyExistsException,
    ARModelFileTooLargeException,
    ARModelNotFoundException,
    InvalidARModelDimensionsException,
    UnsupportedARModelFormatException,
)
from .models import ARModel
from .repository import ARModelRepository
from .schemas import SARModelCreate, SARModelUpdate
from .storage import ARModelStorage


logger = logging.getLogger(__name__)


MAX_FILE_SIZE = 15 * 1024 * 1024

SUPPORTED_FORMATS = {
    "glb",
    "usdz",
}


class ARModelService:

    def __init__(self):
        self.repository = ARModelRepository()
        self.storage = ARModelStorage()

    async def get_model(
        self,
        session: AsyncSession,
        sku: str,
    ) -> ARModel | None:

        model = await self.repository.get_model_by_sku(
            session=session,
            sku=sku,
        )

        if model is None:
            return None

        if model.status != "active":
            return None

        return model

    async def get_model_file(
        self,
        session: AsyncSession,
        sku: str,
    ) -> str:

        model = await self.repository.get_model_by_sku(
            session=session,
            sku=sku,
        )

        if model is None or model.status != "active":
            raise ARModelNotFoundException()

        return model.file_path

    async def create_model(
        self,
        session: AsyncSession,
        sku: str,
        file: UploadFile,
        model_in: SARModelCreate,
    ) -> ARModel:

        logger.info(
            "Creating AR model: sku=%s",
            sku,
        )

        existing_model = (
            await self.repository.get_model_by_sku(
                session=session,
                sku=sku,
            )
        )

        if existing_model is not None:
            raise ARModelAlreadyExistsException()

        file_format = self._get_file_extension(file)

        self._validate_file_size(file)

        filename = f"{sku}.{file_format}"

        file_path = await self.storage.save(
            file=file,
            filename=filename,
        )

        try:
            model = await self.repository.create(
                session=session,
                sku=sku,
                file_path=file_path,
                file_format=file_format,
                width=model_in.width,
                height=model_in.height,
                depth=model_in.depth,
                unit=model_in.unit,
                status="active",
            )

            await session.commit()

        except Exception:
            await session.rollback()

            await self.storage.delete(
                file_path=file_path,
            )

            raise

        logger.info(
            "AR model created: sku=%s id=%s",
            sku,
            model.id,
        )

        return model

    async def update_model(
        self,
        session: AsyncSession,
        sku: str,
        file: UploadFile,
        model_in: SARModelUpdate,
    ) -> ARModel:

        logger.info(
            "Updating AR model: sku=%s",
            sku,
        )

        model = await self.repository.get_model_by_sku(
            session=session,
            sku=sku,
        )

        if model is None:
            raise ARModelNotFoundException()

        old_file_path = model.file_path

        file_format = self._get_file_extension(file)

        self._validate_file_size(file)

        filename = f"{sku}.{file_format}"

        new_file_path = await self.storage.save(
            file=file,
            filename=filename,
        )

        try:
            model = await self.repository.update(
                session=session,
                obj=model,
                file_path=new_file_path,
                file_format=file_format,
                width=model_in.width,
                height=model_in.height,
                depth=model_in.depth,
                unit=model_in.unit,
                status="active",
            )

            await session.commit()

        except Exception:
            await session.rollback()

            await self.storage.delete(
                file_path=new_file_path,
            )

            raise

        if old_file_path != new_file_path:
            await self.storage.delete(
                file_path=old_file_path,
            )

        logger.info(
            "AR model updated: sku=%s id=%s",
            sku,
            model.id,
        )

        return model

    async def delete_model(
        self,
        session: AsyncSession,
        sku: str,
    ) -> None:

        logger.info(
            "Deleting AR model: sku=%s",
            sku,
        )

        model = await self.repository.get_model_by_sku(
            session=session,
            sku=sku,
        )

        if model is None:
            raise ARModelNotFoundException()

        file_path = model.file_path

        await self.repository.delete(
            session=session,
            obj=model,
        )

        try:
            await session.commit()

        except Exception:
            await session.rollback()
            raise

        await self.storage.delete(
            file_path=file_path,
        )

        logger.info(
            "AR model deleted: sku=%s",
            sku,
        )

    @staticmethod
    def _get_file_extension(
        file: UploadFile,
    ) -> str:

        extension = Path(
            file.filename or "",
        ).suffix.lower().lstrip(".")

        if extension not in SUPPORTED_FORMATS:
            raise UnsupportedARModelFormatException()

        return extension

    @staticmethod
    def _validate_file_size(
            file: UploadFile,
    ) -> None:

        if file.size is not None and file.size > MAX_FILE_SIZE:
            raise ARModelFileTooLargeException()

