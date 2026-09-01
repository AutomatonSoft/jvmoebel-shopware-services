import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domains.ingestion.idempotency import is_event_id_unique_violation
from domains.ingestion.validator import validate_http_event
from domains.projections.models.journal import Event

IngestStatus = Literal["accepted", "duplicate"]


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    return uuid.UUID(str(value))


def build_event(body: dict) -> Event:
    return Event(
        event_id=uuid.UUID(str(body["event_id"])),
        event_type=body["event_type"],
        event_version=body["event_version"],
        occurred_at=_parse_datetime(body["occurred_at"]),
        received_at=datetime.now(timezone.utc),
        source=body["source"],
        sales_channel_id=body["sales_channel_id"],
        market_code=body.get("market_code"),
        domain=body.get("domain"),
        language=body.get("language"),
        visitor_id=_parse_uuid(body.get("visitor_id")),
        session_id=_parse_uuid(body.get("session_id")),
        cart_id=_parse_uuid(body.get("cart_id")),
        lead_id=body.get("lead_id"),
        customer_id=body.get("customer_id"),
        order_id=body.get("order_id"),
        contact_id=body.get("contact_id"),
        manual_sale_id=body.get("manual_sale_id"),
        refund_id=body.get("refund_id"),
        aggregate_type=body.get("aggregate_type"),
        aggregate_id=body.get("aggregate_id"),
        aggregate_version=body.get("aggregate_version"),
        correlation_id=_parse_uuid(body.get("correlation_id")),
        consent=body.get("consent"),
        body=body,
    )


async def ingest_http_event(
    session: AsyncSession,
    body: object,
    *,
    origin: str | None,
) -> IngestStatus:
    validated = validate_http_event(body, origin=origin)
    session.add(build_event(validated))

    try:
        await session.flush()
    except IntegrityError as exc:
        if is_event_id_unique_violation(exc):
            await session.rollback()
            return "duplicate"
        raise

    await session.commit()
    return "accepted"
