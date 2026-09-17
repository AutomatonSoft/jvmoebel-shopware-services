from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from core.config import settings

basic_scheme = HTTPBasic(auto_error=False)

WWW_AUTHENTICATE = {"WWW-Authenticate": 'Basic realm="dashboard"'}


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

    user_ok = compare_digest(
        credentials.username,
        settings.dashboard_user.get_secret_value(),
    )
    password_ok = compare_digest(
        credentials.password,
        settings.dashboard_password.get_secret_value(),
    )
    if not (user_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers=WWW_AUTHENTICATE,
        )
