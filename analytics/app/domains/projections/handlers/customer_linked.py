from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id
from domains.projections.models.entities import CustomerLink
from domains.projections.models.journal import Event


async def handle_customer_linked(
    session: AsyncSession,
    event: Event,
) -> None:
    visitor_id = require_id(
        event.visitor_id,
        field="visitor_id",
        event_type=event.event_type,
    )
    customer_id = require_id(
        event.customer_id,
        field="customer_id",
        event_type=event.event_type,
    )
    await session.execute(
        pg_insert(CustomerLink)
        .values(
            visitor_id=visitor_id,
            customer_id=customer_id,
            event_id=event.event_id,
            lead_id=event.lead_id,
            sales_channel_id=event.sales_channel_id,
            occurred_at=event.occurred_at,
        )
        .on_conflict_do_nothing(
            index_elements=["visitor_id", "customer_id"],
        )
    )
