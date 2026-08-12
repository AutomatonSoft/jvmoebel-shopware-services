from domains.base.exceptions import (
    AlreadyExistsException,
    BadRequestException,
    NotFoundException,
)


class ARModelNotFoundException(NotFoundException):
    def __init__(self) -> None:
        super().__init__(
            detail="AR model not found",
        )


class ARModelAlreadyExistsException(
    AlreadyExistsException,
):
    def __init__(self) -> None:
        super().__init__(
            detail="AR model already exists",
        )


class UnsupportedARModelFormatException(
    BadRequestException,
):
    def __init__(self) -> None:
        super().__init__(
            detail="Unsupported AR model format",
        )


class InvalidARModelDimensionsException(
    BadRequestException,
):
    def __init__(self) -> None:
        super().__init__(
            detail="AR model dimensions must be greater than zero",
        )