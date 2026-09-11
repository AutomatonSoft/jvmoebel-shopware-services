from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from domains.ingestion.exceptions import EventValidationError
from domains.ingestion.service import IngestStatus, ingest_http_event

BatchStatus = IngestStatus | Literal["rejected"]


def parse_batch_events(body: object) -> list[Any]:
    if not isinstance(body, dict):
        raise EventValidationError(detail="Batch must be a JSON object")
    events = body.get("events")
    if not isinstance(events, list) or len(events) < 1:
        raise EventValidationError(detail="events must be a non-empty array")
    if len(events) > settings.max_batch_events:
        raise EventValidationError(detail="Batch exceeds max_batch_events")
    return events


async def ingest_http_batch(
    session: AsyncSession,
    events: list[Any],
    *,
    origin: str | None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, item in enumerate(events):
        event_id = item.get("event_id") if isinstance(item, dict) else None
        try:
            status = await ingest_http_event(
                session,
                item,
                origin=origin,
            )
            results.append(
                {
                    "index": index,
                    "event_id": event_id,
                    "status": status,
                }
            )
        except EventValidationError as exc:
            results.append(
                {
                    "index": index,
                    "event_id": event_id,
                    "status": "rejected",
                    "detail": exc.detail,
                }
            )
    return results
