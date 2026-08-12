from fastapi import HTTPException, status


class BadRequestException(HTTPException):
    def __init__(
        self,
        detail: str = "Bad request",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class NotFoundException(HTTPException):
    def __init__(
        self,
        detail: str = "Not found",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class AlreadyExistsException(HTTPException):
    def __init__(
        self,
        detail: str = "Already exists",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class InternalServerException(HTTPException):
    def __init__(
        self,
        detail: str = "Internal server error",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )