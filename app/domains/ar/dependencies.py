from secrets import compare_digest

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings


bearer_scheme = HTTPBearer(
    auto_error=False,
)


async def require_ar_write_access(
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme,
    ),
) -> None:

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    expected_token = settings.ar_write_api_key.get_secret_value()

    if not compare_digest(
        credentials.credentials,
        expected_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )