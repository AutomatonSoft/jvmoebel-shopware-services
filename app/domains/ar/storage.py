from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from core.config import settings


class ARModelStorage:

    def __init__(self):
        self.base_path = Path(
            settings.ar_models_storage_path
        )

        self.base_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    async def save(
        self,
        file: UploadFile,
        sku: str,
        file_format: str,
    ) -> str:

        sku_path = self.base_path / sku

        sku_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = f"{uuid4().hex}.{file_format}"

        file_path = sku_path / filename

        with file_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                destination.write(chunk)

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

