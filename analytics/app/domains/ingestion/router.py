from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import get_async_session
from domains.base.dependencies import require_ingest_access
from domains.ingestion.sales_channels import resolve_request_origin
from domains.ingestion.service import ingest_http_event

router = APIRouter(
    prefix="/events",
    tags=["Ingestion"],
)


@router.post(
    "",
    dependencies=[Depends(require_ingest_access)],
)
async def ingest_event(
    request: Request,
    body: dict,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    status = await ingest_http_event(
        session,
        body,
        origin=resolve_request_origin(request),
    )
    return {"status": status}
