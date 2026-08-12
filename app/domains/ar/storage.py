from pathlib import Path

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
        filename: str,
    ) -> str:

        file_path = self.base_path / filename

        with file_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                destination.write(chunk)

        return str(file_path)

    async def delete(
        self,
        file_path: str,
    ) -> None:

        path = Path(file_path)

        if path.exists():
            path.unlink()