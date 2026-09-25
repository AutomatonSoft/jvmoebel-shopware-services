from uuid import UUID

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.base.exceptions import NotFoundException
from domains.journeys.schemas import JourneyEvent, JourneyResponse
from domains.projections.models.entities import Session
from domains.projections.models.facts import Refund
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload


def to_journey_event(
    event: Event,
    *,
    traffic_source: str | None = None,
    invalid_reason: str | None = None,
) -> JourneyEvent:
    return JourneyEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        received_at=event.received_at,
        source=event.source,
        sales_channel_id=event.sales_channel_id,
        visitor_id=event.visitor_id,
        session_id=event.session_id,
        lead_id=event.lead_id,
        customer_id=event.customer_id,
        order_id=event.order_id,
        contact_id=event.contact_id,
        manual_sale_id=event.manual_sale_id,
        refund_id=event.refund_id,
        traffic_source=traffic_source,
        invalid_reason=invalid_reason,
        payload=event_payload(event),
    )


async def list_events(
    session: AsyncSession,
    clause: ColumnElement[bool],
    *,
    limit: int | None = None,
) -> list[Event]:
    stmt = (
        select(Event)
        .where(clause)
        .order_by(Event.occurred_at.asc(), Event.event_id.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await session.scalars(stmt)
    return list(result.all())


async def _session_traffic_sources(
    session: AsyncSession,
    events: list[Event],
) -> dict[UUID, str]:
    session_ids = [
        event.session_id
        for event in events
        if event.event_type == "session_started" and event.session_id is not None
    ]
    if not session_ids:
        return {}
    stmt = select(Session.session_id, Session.source).where(
        Session.session_id.in_(session_ids),
        Session.source.isnot(None),
    )
    result = await session.execute(stmt)
    return {session_id: source for session_id, source in result.all()}


async def _refund_invalid_reasons(
    session: AsyncSession,
    events: list[Event],
) -> dict[str, str]:
    refund_ids = [
        event.refund_id
        for event in events
        if event.event_type == "refund_created" and event.refund_id is not None
    ]
    if not refund_ids:
        return {}
    stmt = select(Refund.refund_id, Refund.invalid_reason).where(
        Refund.refund_id.in_(refund_ids),
        Refund.invalid_reason.isnot(None),
    )
    result = await session.execute(stmt)
    return {refund_id: reason for refund_id, reason in result.all()}


async def load_journey(
    session: AsyncSession,
    clause: ColumnElement[bool],
) -> JourneyResponse:
    events = await list_events(session, clause)
    if not events:
        raise NotFoundException(detail="Journey not found")
    traffic_by_session = await _session_traffic_sources(session, events)
    refund_reasons = await _refund_invalid_reasons(session, events)
    return JourneyResponse(
        events=[
            to_journey_event(
                event,
                traffic_source=(
                    traffic_by_session.get(event.session_id)  # type: ignore
                    if event.event_type == "session_started"
                    else None
                ),
                invalid_reason=(
                    refund_reasons.get(event.refund_id)
                    if event.event_type == "refund_created" and event.refund_id
                    else None
                ),
            )
            for event in events
        ]
    )
