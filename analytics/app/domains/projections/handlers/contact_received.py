from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id
from domains.projections.models.facts import Contact
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload


async def handle_contact_received(
    session: AsyncSession,
    event: Event,
) -> None:
    contact_id = require_id(
        event.contact_id,
        field="contact_id",
        event_type=event.event_type,
    )
    lead_id = require_id(
        event.lead_id,
        field="lead_id",
        event_type=event.event_type,
    )
    payload = event_payload(event)
    await session.execute(
        pg_insert(Contact)
        .values(
            contact_id=contact_id,
            event_id=event.event_id,
            lead_id=lead_id,
            visitor_id=event.visitor_id,
            sales_channel_id=event.sales_channel_id,
            market_code=event.market_code,
            contact_channel=payload["contact_channel"],
            contact_type=payload["contact_type"],
            tracking_reference=payload.get("tracking_reference"),
            provider_reference=payload.get("provider_reference"),
            product_number=payload.get("product_number"),
            occurred_at=event.occurred_at,
        )
        .on_conflict_do_nothing(index_elements=["contact_id"])
    )
