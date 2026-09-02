from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id
from domains.projections.models.facts import ContactIntent
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload


async def handle_contact_intent(
    session: AsyncSession,
    event: Event,
) -> None:
    visitor_id = require_id(
        event.visitor_id,
        field="visitor_id",
        event_type=event.event_type,
    )
    payload = event_payload(event)
    session.add(
        ContactIntent(
            event_id=event.event_id,
            visitor_id=visitor_id,
            session_id=event.session_id,
            sales_channel_id=event.sales_channel_id,
            channel=payload["channel"],
            action=payload.get("action"),
            occurred_at=event.occurred_at,
        )
    )
