from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.models.facts import PaymentMethodEvent
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload


async def handle_payment_failed(
    session: AsyncSession,
    event: Event,
) -> None:
    payload = event_payload(event)
    session.add(
        PaymentMethodEvent(
            event_id=event.event_id,
            payment_method=payload["payment_method"],
            visitor_id=event.visitor_id,
            session_id=event.session_id,
            cart_id=event.cart_id,
            sales_channel_id=event.sales_channel_id,
            market_code=event.market_code,
            kind="failed",
            error_category=payload.get("error_category"),
            error_code=payload.get("error_code"),
            error_stage=payload.get("stage"),
            occurred_at=event.occurred_at,
        )
    )
