from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import ProjectionInvariantError
from domains.projections.models.facts import PaymentMethodEvent
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload


async def handle_payment_methods_shown(
    session: AsyncSession,
    event: Event,
) -> None:
    payload = event_payload(event)
    methods = payload.get("methods")
    if not isinstance(methods, list):
        raise ProjectionInvariantError(
            f"{event.event_type} missing required methods list"
        )
    for method in methods:
        session.add(
            PaymentMethodEvent(
                event_id=event.event_id,
                payment_method=method,
                visitor_id=event.visitor_id,
                session_id=event.session_id,
                cart_id=event.cart_id,
                sales_channel_id=event.sales_channel_id,
                kind="shown",
                occurred_at=event.occurred_at,
            )
        )
