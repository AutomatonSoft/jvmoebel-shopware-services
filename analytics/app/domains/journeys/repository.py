from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.base.exceptions import NotFoundException
from domains.journeys.schemas import JourneyEvent, JourneyResponse
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload


def to_journey_event(event: Event) -> JourneyEvent:
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


async def load_journey(
    session: AsyncSession,
    clause: ColumnElement[bool],
) -> JourneyResponse:
    events = await list_events(session, clause)
    if not events:
        raise NotFoundException(detail="Journey not found")
    return JourneyResponse(events=[to_journey_event(event) for event in events])
