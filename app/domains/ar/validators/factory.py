from pathlib import Path
from domains.ar.validators.glb_validator import GLBValidator
from domains.ar.validators.usdz_validator import USDZValidator
from domains.ar.exceptions import (
    UnsupportedARModelFormatException,
)


class ValidatorFactory:
    _validators = {
        ".glb": GLBValidator,
        ".usdz": USDZValidator,
    }

    @classmethod
    def validate(cls, file_path: Path) -> bool:
        # ТЗ GLB-1: Расширение файла = .glb
        # ТЗ USDZ-1: Расширение файла = .usdz
        extension = file_path.suffix.lower()
        validator_class = cls._validators.get(extension)

        if not validator_class:
            raise UnsupportedARModelFormatException()

        validator = validator_class()

        try:
            return validator.validate(file_path)
        except Exception:
            raise