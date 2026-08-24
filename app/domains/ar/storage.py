from pathlib import Path
from uuid import uuid4
import hashlib

from anyio import open_file
from fastapi import UploadFile

from core.config import settings


class ARModelStorage:

    def __init__(self):
        self.base_path = Path(
            settings.ar_models_storage_path
        ).resolve()

        self.base_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _sku_to_storage_key(sku: str) -> str:
        # Используем первые 16 символов SHA256 для краткости
        return hashlib.sha256(sku.encode('utf-8')).hexdigest()[:16]

    async def save(
            self,
            file: UploadFile,
            sku: str,
            file_format: str,
    ) -> str:

        storage_key = self._sku_to_storage_key(sku)
        sku_path = self.base_path / storage_key

        sku_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = f"{uuid4().hex}.{file_format}"

        file_path = sku_path / filename

        if self.base_path not in file_path.resolve().parents:
            raise ValueError("Invalid storage path")

        async with await open_file(file_path, "wb") as destination:
            while chunk := await file.read(1024 * 1024):
                await destination.write(chunk)

        return str(file_path)

    async def delete(
            self,
            file_path: str,
    ) -> None:

        path = Path(file_path)

        if path.is_file():
            path.unlink()

    async def exists(
            self,
            file_path: str,
    ) -> bool:

        return Path(file_path).is_file()
