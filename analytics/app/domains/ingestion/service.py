import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from domains.ingestion.exceptions import EventIdCollisionError, EventValidationError
from domains.ingestion.idempotency import is_same_event
from domains.ingestion.validator import validate_http_event, validate_rabbit_event
from domains.projections.dispatcher import dispatch
from domains.projections.models.entities import Visitor
from domains.projections.models.journal import Event
from domains.projections.parsing import parse_datetime
from domains.projections.stubs import ensure_stubs
from domains.visitors.redact import redact_event_body

IngestStatus = Literal["accepted", "duplicate"]


def _parse_rfc3339(field: str, value: object) -> datetime:
    if not isinstance(value, str):
        raise EventValidationError(detail=f"{field} must be an RFC3339 date-time")
    try:
        return parse_datetime(value)
    except ValueError as exc:
        raise EventValidationError(
            detail=f"{field} must be an RFC3339 date-time",
        ) from exc


def _parse_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    return uuid.UUID(str(value))


def event_row_values(body: dict) -> dict:
    return {
        "event_id": uuid.UUID(str(body["event_id"])),
        "event_type": body["event_type"],
        "event_version": body["event_version"],
        "occurred_at": _parse_rfc3339("occurred_at", body["occurred_at"]),
        "received_at": datetime.now(timezone.utc),
        "source": body["source"],
        "sales_channel_id": body["sales_channel_id"],
        "market_code": body.get("market_code"),
        "domain": body.get("domain"),
        "language": body.get("language"),
        "visitor_id": _parse_uuid(body.get("visitor_id")),
        "session_id": _parse_uuid(body.get("session_id")),
        "cart_id": _parse_uuid(body.get("cart_id")),
        "lead_id": body.get("lead_id"),
        "customer_id": body.get("customer_id"),
        "order_id": body.get("order_id"),
        "contact_id": body.get("contact_id"),
        "manual_sale_id": body.get("manual_sale_id"),
        "refund_id": body.get("refund_id"),
        "aggregate_type": body.get("aggregate_type"),
        "aggregate_id": body.get("aggregate_id"),
        "aggregate_version": body.get("aggregate_version"),
        "correlation_id": _parse_uuid(body.get("correlation_id")),
        "consent": body.get("consent"),
        "body": body,
    }


async def persist_validated_event(
    session: AsyncSession,
    body: dict,
) -> IngestStatus:
    values = event_row_values(body)
    event_id = values["event_id"]
    result = await session.execute(
        pg_insert(Event)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["event_id"])
        .returning(Event.event_id)
    )
    inserted_id = result.scalar_one_or_none()
    if inserted_id is None:
        existing = await session.get(Event, event_id)
        if existing is None:
            raise RuntimeError("Conflicting event was not readable")
        if is_same_event(existing, values):
            return "duplicate"
        raise EventIdCollisionError()

    event = await session.get(Event, event_id)
    if event is None:
        raise RuntimeError("Inserted event was not readable")

    await ensure_stubs(session, event)
    if event.visitor_id is not None:
        visitor = await session.get(
            Visitor,
            event.visitor_id,
            with_for_update=True,
        )
        if visitor is not None and visitor.anonymized_at is not None:
            event.body = redact_event_body(event.body)
            flag_modified(event, "body")
    await dispatch(session, event)
    return "accepted"


async def ingest_http_event(
    session: AsyncSession,
    body: object,
    *,
    origin: str | None,
) -> IngestStatus:
    validated = validate_http_event(body, origin=origin)
    async with session.begin():
        return await persist_validated_event(session, validated)


async def ingest_rabbit_event(
    session: AsyncSession,
    body: object,
) -> IngestStatus:
    validated = validate_rabbit_event(body)
    async with session.begin():
        return await persist_validated_event(session, validated)
