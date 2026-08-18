# app/domains/ar/validators/sku.py

import re

# Константы
SKU_MAX_LENGTH = 64

# Простой паттерн без look-ahead для Pydantic
# Разрешает только буквы, цифры, _ и - после первого символа
SKU_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"


def is_valid_sku(sku: str) -> bool:
    """
    Validate SKU for filesystem safety.
    Checks:
    - Length (1-64 chars)
    - Allowed chars (alphanumeric, _, -)
    - No path separators (/ or \)
    - No path traversal (..)
    - No null bytes
    - First char not _ or -
    """
    if not sku:
        return False
    if len(sku) > SKU_MAX_LENGTH:
        return False

    # Базовый паттерн
    if not re.match(SKU_PATTERN, sku):
        return False

    # Дополнительные проверки безопасности (без look-ahead)
    unsafe_patterns = [
        r"\.\.",  # path traversal
        r"[/\\]",  # path separators
        r"\0",  # null byte
    ]

    for pattern in unsafe_patterns:
        if re.search(pattern, sku):
            return False

    return True


def validate_sku_or_raise(sku: str) -> None:
    """
    Validate SKU and raise ValueError if invalid.
    """
    if not is_valid_sku(sku):
        raise ValueError(
            f"Invalid SKU: '{sku}'. SKU must contain only alphanumeric characters, "
            f"underscore and hyphen. Must not contain path separators, "
            f"path traversal (..), or null bytes."
        )