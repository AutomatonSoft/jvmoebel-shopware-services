from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from domains.base.exceptions import NotFoundException
from domains.projections.models.entities import (
    Lead,
    ManualSale,
    Order,
    Session,
    Visitor,
)
from domains.projections.models.facts import AttributionTouch
from domains.projections.models.journal import Event
from domains.visitors.redact import (
    SESSION_IDENTIFYING_FIELDS,
    SNAPSHOT_IDENTIFYING_FIELDS,
    TOUCH_IDENTIFYING_FIELDS,
    VISITOR_IDENTIFYING_FIELDS,
    identifying_nulls,
    redact_event_body,
)
from domains.visitors.schemas import AnonymizeVisitorResponse


async def anonymize_visitor(
    session: AsyncSession,
    visitor_id: UUID,
) -> AnonymizeVisitorResponse:
    async with session.begin():
        visitor = await session.get(
            Visitor,
            visitor_id,
            with_for_update=True,
        )
        if visitor is None:
            raise NotFoundException(detail="Visitor not found")
        if visitor.anonymized_at is not None:
            return AnonymizeVisitorResponse(status="already_anonymized")

        for field in VISITOR_IDENTIFYING_FIELDS:
            setattr(visitor, field, None)
        visitor.anonymized_at = datetime.now(timezone.utc)

        await session.execute(
            update(Session)
            .where(Session.visitor_id == visitor_id)
            .values(**identifying_nulls(SESSION_IDENTIFYING_FIELDS))
        )
        await session.execute(
            update(AttributionTouch)
            .where(AttributionTouch.visitor_id == visitor_id)
            .values(**identifying_nulls(TOUCH_IDENTIFYING_FIELDS))
        )
        snapshot_values = identifying_nulls(SNAPSHOT_IDENTIFYING_FIELDS)
        await session.execute(
            update(Lead).where(Lead.visitor_id == visitor_id).values(**snapshot_values)
        )
        await session.execute(
            update(Order)
            .where(Order.visitor_id == visitor_id)
            .values(**snapshot_values)
        )
        await session.execute(
            update(ManualSale)
            .where(ManualSale.visitor_id == visitor_id)
            .values(**snapshot_values)
        )

        events = await session.scalars(
            select(Event).where(Event.visitor_id == visitor_id)
        )
        for event in events:
            event.body = redact_event_body(event.body)
            flag_modified(event, "body")

        return AnonymizeVisitorResponse(status="anonymized")
