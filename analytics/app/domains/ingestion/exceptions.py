from fastapi import HTTPException, status


class EventValidationError(HTTPException):
    def __init__(
        self,
        detail: str = "Invalid event",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )
