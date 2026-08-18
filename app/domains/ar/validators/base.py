# app/domains/ar/validators/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from app.core.config import settings
from app.domains.ar.exceptions import ARModelFileTooLargeException


class BaseValidator(ABC):
    @abstractmethod
    def validate(self, file_path: Path) -> bool:
        """Валидация файла"""
        pass

    def _check_size(self, file_path: Path) -> None:
        """Проверка размера файла"""
        try:
            size = file_path.stat().st_size
            if size > settings.ar_max_file_size:
                raise ARModelFileTooLargeException()
        except OSError:
            # Если не можем получить размер - считаем файл невалидным
            raise ARModelFileTooLargeException()