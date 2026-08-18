from pathlib import Path
from app.domains.ar.validators.base import BaseValidator
from app.domains.ar.validators.glb_validator import GLBValidator
from app.domains.ar.validators.usdz_validator import USDZValidator
from app.domains.ar.exceptions import (
    UnsupportedARModelFormatException,
    InvalidARModelFileException,
)


class ValidatorFactory:
    _validators = {
        '.glb': GLBValidator,
        '.usdz': USDZValidator,
    }

    @classmethod
    def validate(cls, file_path: Path) -> bool:
        extension = file_path.suffix.lower()
        validator_class = cls._validators.get(extension)

        if not validator_class:
            raise UnsupportedARModelFormatException()

        validator = validator_class()

        try:
            return validator.validate(file_path)
        except Exception:
            # Пробрасываем исключение дальше (ARModelFileTooLargeException или другие)
            raise