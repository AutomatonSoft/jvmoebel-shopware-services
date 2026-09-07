from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import get_async_session
from domains.base.dependencies import require_ingest_access
from domains.ingestion.batch import ingest_http_batch, parse_batch_events
from domains.ingestion.rate_limit import enforce_ingest_rate_limit
from domains.ingestion.sales_channels import resolve_request_origin
from domains.ingestion.service import ingest_http_event

router = APIRouter(
    prefix="/events",
    tags=["Ingestion"],
    dependencies=[
        Depends(enforce_ingest_rate_limit),
        Depends(require_ingest_access),
    ],
)


@router.post("/batch")
async def ingest_event_batch(
    request: Request,
    body: dict,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    events = parse_batch_events(body)
    results = await ingest_http_batch(
        session,
        events,
        origin=resolve_request_origin(request),
    )
    return {"results": results}


@router.post("")
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
