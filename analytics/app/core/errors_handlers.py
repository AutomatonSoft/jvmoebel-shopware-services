import html
import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.exc import ProgrammingError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)


def is_dashboard_request(request: Request) -> bool:
    path = request.url.path
    return path == "/dashboard" or path.startswith("/dashboard/")


def dashboard_error(
    status_code: int,
    detail: str,
    headers: Mapping[str, str] | None = None,
) -> HTMLResponse:
    body = (
        '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">'
        "<title>Analytics</title></head><body>"
        f"<h1>{status_code}</h1><p>{html.escape(detail)}</p>"
        '<p><a href="/dashboard">Analytics</a></p></body></html>'
    )
    return HTMLResponse(content=body, status_code=status_code, headers=headers)


def _http_detail(detail: object) -> str:
    if isinstance(detail, str):
        return detail
    return "Invalid request"


def register_errors_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ):
        if is_dashboard_request(request):
            return dashboard_error(422, "Некорректный запрос")
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(StarletteHTTPException)
    def handle_http_exception(request: Request, exc: StarletteHTTPException):
        if is_dashboard_request(request):
            return dashboard_error(
                exc.status_code,
                _http_detail(exc.detail),
                exc.headers,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(ProgrammingError)
    def handle_programming_error(
        request: Request,
        exc: ProgrammingError,
    ):
        error_msg = str(exc)
        log.error(f"Programming error: {error_msg}", exc_info=exc)

        if "UndefinedTableError" in error_msg or "does not exist" in error_msg:
            detail = "Database schema is not ready. Apply Alembic migrations."
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            detail = "An unexpected database error has occurred."
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        if is_dashboard_request(request):
            return dashboard_error(status_code, detail)
        return JSONResponse(
            status_code=status_code,
            content={"message": detail},
        )

    @app.exception_handler(Exception)
    def handle_any_other_error(request: Request, exc: Exception):
        log.error(f"Unhandled error: {exc}", exc_info=exc)
        detail = "An unexpected error has occurred."
        if is_dashboard_request(request):
            return dashboard_error(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail,
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": detail},
        )
