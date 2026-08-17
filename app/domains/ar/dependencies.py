from secrets import compare_digest

from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from domains.base.exceptions import UnauthorizedException


bearer_scheme = HTTPBearer(
    auto_error=False,
)


async def require_ar_write_access(
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme,
    ),
) -> None:

    if credentials is None:
        raise UnauthorizedException(
            detail="Authentication required",
        )

    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedException(
            detail="Invalid authentication scheme",
        )

    expected_token = settings.ar_write_api_key.get_secret_value()

    if not compare_digest(
        credentials.credentials,
        expected_token,
    ):
        raise UnauthorizedException(
            detail="Invalid authentication token",
        )