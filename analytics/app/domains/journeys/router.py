from fastapi import APIRouter, Depends

from domains.base.dependencies import require_read_access

router = APIRouter(
    prefix="/analytics",
    tags=["Journeys"],
    dependencies=[Depends(require_read_access)],
)
