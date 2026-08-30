from fastapi import APIRouter, Depends

from domains.base.dependencies import require_ingest_access

router = APIRouter(
    prefix="/events",
    tags=["Ingestion"],
)


@router.post(
    "",
    dependencies=[Depends(require_ingest_access)],
)
async def ingest_event() -> dict[str, str]:
    return {"status": "accepted"}
