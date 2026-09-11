from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import get_async_session
from domains.base.dependencies import require_ingest_access
from domains.ingestion.batch import ingest_http_batch, parse_batch_events
from domains.ingestion.rate_limit import enforce_ingest_rate_limit
from domains.ingestion.sales_channels import resolve_request_origin
from domains.ingestion.schemas import IngestBatchResponse, IngestEventResponse
from domains.ingestion.service import ingest_http_event

router = APIRouter(
    prefix="/events",
    tags=["Ingestion"],
    dependencies=[
        Depends(require_ingest_access),
        Depends(enforce_ingest_rate_limit),
    ],
)

INGEST_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "description": "Missing or invalid ingest API key",
    },
    413: {
        "description": "HTTP request body exceeds MAX_BODY_SIZE",
    },
    422: {
        "description": (
            "Schema, allowlist, origin/domain, unknown sales_channel_id, "
            "or invalid batch envelope"
        ),
    },
    429: {
        "description": "HTTP ingest rate limit exceeded. Retry-After is in seconds",
    },
}


@router.post(
    "/batch",
    response_model=IngestBatchResponse,
    responses=INGEST_RESPONSES,
)
async def ingest_event_batch(
    request: Request,
    body: dict,
    session: AsyncSession = Depends(get_async_session),
) -> IngestBatchResponse:
    events = parse_batch_events(body)
    results = await ingest_http_batch(
        session,
        events,
        origin=resolve_request_origin(request),
    )
    return IngestBatchResponse.model_validate({"results": results})


@router.post(
    "",
    response_model=IngestEventResponse,
    responses=INGEST_RESPONSES,
)
async def ingest_event(
    request: Request,
    body: dict,
    session: AsyncSession = Depends(get_async_session),
) -> IngestEventResponse:
    status = await ingest_http_event(
        session,
        body,
        origin=resolve_request_origin(request),
    )
    return IngestEventResponse(status=status)
