from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from core.config import settings
from domains.base.exceptions import UnauthorizedException

bearer_scheme = HTTPBearer(
    auto_error=False,
)
basic_scheme = HTTPBasic(auto_error=False)

WWW_AUTHENTICATE = {"WWW-Authenticate": 'Basic realm="dashboard"'}


def dashboard_credentials_ok(username: str, password: str) -> bool:
    user_ok = compare_digest(
        username,
        settings.dashboard_user.get_secret_value(),
    )
    password_ok = compare_digest(
        password,
        settings.dashboard_password.get_secret_value(),
    )
    return user_ok and password_ok


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
    bearer: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ],
    basic: Annotated[
        HTTPBasicCredentials | None,
        Security(basic_scheme),
    ],
) -> None:
    if basic is not None:
        if dashboard_credentials_ok(basic.username, basic.password):
            return
        raise UnauthorizedException(
            detail="Invalid authentication token",
        )
    _validate_bearer_token(
        bearer,
        settings.analytics_read_api_key.get_secret_value(),
    )


async def require_dashboard_access(
    credentials: Annotated[
        HTTPBasicCredentials | None,
        Depends(basic_scheme),
    ],
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers=WWW_AUTHENTICATE,
        )
    if dashboard_credentials_ok(credentials.username, credentials.password):
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers=WWW_AUTHENTICATE,
    )
