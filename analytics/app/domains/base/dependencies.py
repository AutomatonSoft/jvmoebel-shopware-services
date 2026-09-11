from secrets import compare_digest

from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from domains.base.exceptions import UnauthorizedException


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def _validate_bearer_token(
    credentials: HTTPAuthorizationCredentials | None,
    expected_token: str,
) -> None:
    if credentials is None:
        raise UnauthorizedException(
            detail="Authentication required",
        )

    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedException(
            detail="Invalid authentication scheme",
        )

    if not compare_digest(
        credentials.credentials,
        expected_token,
    ):
        raise UnauthorizedException(
            detail="Invalid authentication token",
        )


async def require_ingest_access(
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme,
    ),
) -> None:
    _validate_bearer_token(
        credentials,
        settings.analytics_ingest_api_key.get_secret_value(),
    )


async def require_read_access(
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme,
    ),
) -> None:
    _validate_bearer_token(
        credentials,
        settings.analytics_read_api_key.get_secret_value(),
    )
