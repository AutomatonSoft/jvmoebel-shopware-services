import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import ProgrammingError

log = logging.getLogger(__name__)


def register_errors_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProgrammingError)
    def handle_programming_error(
            request: Request,
            exc: ProgrammingError,
    ) -> JSONResponse:
        error_msg = str(exc)
        log.error(f"Programming error: {error_msg}", exc_info=exc)

        # Проверяем, является ли ошибка отсутствием таблицы
        if "UndefinedTableError" in error_msg or "does not exist" in error_msg:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "message": "Database schema is not ready. Apply Alembic migrations."
                },
            )

        # Любая другая ошибка программирования
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An unexpected database error has occurred."
            },
        )

    @app.exception_handler(Exception)
    def handle_any_other_error(
            request: Request,
            exc: Exception,
    ) -> JSONResponse:
        log.error(f"Unhandled error: {exc}", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An unexpected error has occurred."
            },
        )