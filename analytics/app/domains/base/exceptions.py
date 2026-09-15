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


class UnauthorizedException(HTTPException):
    def __init__(
        self,
        detail: str = "Unauthorized",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class TooManyRequestsException(HTTPException):
    def __init__(
        self,
        retry_after: int,
        detail: str = "Rate limit exceeded",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
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