# app/domains/ar/service.py

import logging
from decimal import Decimal
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import (
    ARModelAlreadyExistsException,
    ARModelFileTooLargeException,
    ARModelNotFoundException,
    ARModelFileNotFoundException,
    InvalidARModelDimensionsException,
    UnsupportedARModelFormatException,
)
from .models import ARModel
from .repository import ARModelRepository
from .schemas import (
    SARModelCreate,
    SARModelStatusUpdate,
    SARModelUpdate,
)
from .storage import ARModelStorage

#опасный импорт, так как файл сгенерированный гпт и непроверенный
from .validators import validate_model_file


logger = logging.getLogger(__name__)


MAX_FILE_SIZE = 15 * 1024 * 1024
FILE_CHECK_CHUNK_SIZE = 1024 * 1024

SUPPORTED_FORMATS = {
    "glb",
    "usdz",
}

UNIT_TO_METERS = {
    "m": Decimal("1"),
    "cm": Decimal("0.01"),
    "mm": Decimal("0.001"),
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

        if not await self.storage.exists(
            file_path=model.file_path,
        ):
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

        if not await self.storage.exists(
            file_path=model.file_path,
        ):
            raise ARModelFileNotFoundException()

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

        await self._validate_file_size(file)

        await validate_model_file(
            file=file,
            file_format=file_format,
        )

        width, height, depth = self._convert_dimensions_to_meters(
            width=model_in.width,
            height=model_in.height,
            depth=model_in.depth,
            unit=model_in.unit,
        )

        file_path = await self.storage.save(
            file=file,
            sku=sku,
            file_format=file_format,
        )

        try:
            model = await self.repository.create(
                session=session,
                sku=sku,
                file_path=file_path,
                file_format=file_format,
                width=width,
                height=height,
                depth=depth,
                unit="m",
                status="active",
            )

            await session.commit()

        except IntegrityError:
            await session.rollback()

            await self.storage.delete(
                file_path=file_path,
            )

            raise ARModelAlreadyExistsException()

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

        await self._validate_file_size(file)

        await validate_model_file(
            file=file,
            file_format=file_format,
        )

        width, height, depth = self._convert_dimensions_to_meters(
            width=model_in.width,
            height=model_in.height,
            depth=model_in.depth,
            unit=model_in.unit,
        )

        new_file_path = await self.storage.save(
            file=file,
            sku=sku,
            file_format=file_format,
        )

        try:
            model = await self.repository.update(
                session=session,
                obj=model,
                file_path=new_file_path,
                file_format=file_format,
                width=width,
                height=height,
                depth=depth,
                unit="m",
                status="active",
            )

            await session.commit()

        except Exception:
            await session.rollback()

            await self.storage.delete(
                file_path=new_file_path,
            )

            raise

        # Эту проверку оставляем на случай, если изменим логику формирования пути на ту,
        # которая потенциально может создавать одинаковые пути
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

    async def update_status(
        self,
        session: AsyncSession,
        sku: str,
        status_in: SARModelStatusUpdate,
    ) -> ARModel:

        logger.info(
            "Updating AR model status: sku=%s status=%s",
            sku,
            status_in.status,
        )

        model = await self.repository.get_model_by_sku(
            session=session,
            sku=sku,
        )

        if model is None:
            raise ARModelNotFoundException()

        model.status = status_in.status

        try:
            await session.commit()

        except Exception:
            await session.rollback()
            raise

        logger.info(
            "AR model status updated: sku=%s status=%s",
            sku,
            model.status,
        )

        return model

    async def delete_model(
            self,
            session: AsyncSession,
            sku: str,
    ) -> None:
        """
        При удалении файла удаления файла, может возникнуть ситуация, в ходе которой запись из бд удалиться,
        а сам файл - нет. И он станет осиротевшим - orphan-файл

        Сейчас это решается просто предупреждением в логировании. И такие файлы нужно удалять вручную.
        Потом можно вынести задачу в фон
        """
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

        if await self.storage.exists(
                file_path=file_path,
        ):
            logger.error(
                "AR model file still exists after deletion: "
                "sku=%s file_path=%s. Manual deletion required.",
                sku,
                file_path,
            )

        logger.info(
            "AR model deleted: sku=%s",
            sku,
        )

    @staticmethod
    def _convert_dimensions_to_meters(
        width: Decimal,
        height: Decimal,
        depth: Decimal,
        unit: str,
    ) -> tuple[Decimal, Decimal, Decimal]:

        multiplier = UNIT_TO_METERS.get(unit)

        if multiplier is None:
            raise InvalidARModelDimensionsException()

        return (
            width * multiplier,
            height * multiplier,
            depth * multiplier,
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
    async def _validate_file_size(
            file: UploadFile,
    ) -> None:

        if file.size is not None:
            if file.size > MAX_FILE_SIZE:
                raise ARModelFileTooLargeException()

            return

        total_size = 0

        while total_size < MAX_FILE_SIZE:
            chunk = await file.read(
                min(
                    FILE_CHECK_CHUNK_SIZE,
                    MAX_FILE_SIZE - total_size,
                ),
            )

            if not chunk:
                await file.seek(0)
                return

            total_size += len(chunk)

        extra_byte = await file.read(1)

        await file.seek(0)

        if extra_byte:
            raise ARModelFileTooLargeException()