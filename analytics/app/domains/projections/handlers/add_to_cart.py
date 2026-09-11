from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id
from domains.projections.models.facts import CartAdd
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload, parse_money


async def handle_add_to_cart(
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
        CartAdd(
            event_id=event.event_id,
            visitor_id=visitor_id,
            session_id=event.session_id,
            cart_id=event.cart_id,
            sales_channel_id=event.sales_channel_id,
            market_code=event.market_code,
            sku=payload["sku"],
            quantity=payload["quantity"],
            price=parse_money(payload.get("unit_price")),
            currency=payload.get("currency"),
            occurred_at=event.occurred_at,
        )
    )
