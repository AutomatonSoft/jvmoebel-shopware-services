from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id
from domains.projections.models.facts import Refund, RefundLine
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload, parse_datetime, parse_money


async def handle_refund_created(
    session: AsyncSession,
    event: Event,
) -> None:
    refund_id = require_id(
        event.refund_id,
        field="refund_id",
        event_type=event.event_type,
    )
    order_id = require_id(
        event.order_id,
        field="order_id",
        event_type=event.event_type,
    )
    payload = event_payload(event)
    session.add(
        Refund(
            refund_id=refund_id,
            event_id=event.event_id,
            order_id=order_id,
            order_number=payload.get("order_number"),
            sales_channel_id=event.sales_channel_id,
            refund_amount=parse_money(payload["refund_amount"]),
            currency=payload["currency"],
            refund_type=payload["refund_type"],
            payment_method=payload.get("payment_method"),
            order_state=payload.get("order_state"),
            payment_state=payload.get("payment_state"),
            refunded_at=parse_datetime(payload["refunded_at"]),
        )
    )
    for item in payload.get("line_items") or []:
        session.add(
            RefundLine(
                refund_id=refund_id,
                line_item_id=item["line_item_id"],
                product_number=item.get("product_number"),
                item_type=item["item_type"],
                quantity=item["quantity"],
                unit_price=parse_money(item["unit_price"]),
                total_price=parse_money(item["total_price"]),
            )
        )
