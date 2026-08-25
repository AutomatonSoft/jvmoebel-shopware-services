# app/domains/ar/validators/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from core.config import settings
from domains.ar.exceptions import ARModelFileTooLargeException


class BaseValidator(ABC):
    @abstractmethod
    def validate(self, file_path: Path) -> bool:
        """Валидация файла"""
        pass

    def _check_size(self, file_path: Path) -> None:
        # ТЗ GLB-10 / USDZ-11: Файл <= AR_MAX_FILE_SIZE
        try:
            size = file_path.stat().st_size
            if size > settings.ar_max_file_size:
                raise ARModelFileTooLargeException()
        except OSError:
            raise ARModelFileTooLargeException()