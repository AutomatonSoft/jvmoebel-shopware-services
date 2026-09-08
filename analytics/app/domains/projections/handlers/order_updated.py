from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import copy_attribution_snapshot
from domains.projections.exceptions import require_id, require_row
from domains.projections.models.entities import Order, Visitor
from domains.projections.models.journal import Event
from domains.projections.order_lines import replace_order_lines
from domains.projections.parsing import event_payload, parse_money
from domains.projections.versioning import should_apply_entity_update


async def handle_order_updated(
    session: AsyncSession,
    event: Event,
) -> None:
    order_id = require_id(
        event.order_id,
        field="order_id",
        event_type=event.event_type,
    )
    order = require_row(
        await session.get(Order, order_id),
        entity="order",
        event_type=event.event_type,
    )
    if order.paid_event_id is not None:
        return
    if not should_apply_entity_update(
        is_stub=order.is_stub,
        stored_aggregate_version=order.aggregate_version,
        incoming_aggregate_version=event.aggregate_version,
        stored_occurred_at=order.last_event_occurred_at,
        incoming_occurred_at=event.occurred_at,
        has_version_column=True,
    ):
        return

    payload = event_payload(event)
    order.order_number = payload.get("order_number")
    if event.visitor_id is not None:
        order.visitor_id = event.visitor_id
    if event.session_id is not None:
        order.session_id = event.session_id
    if event.cart_id is not None:
        order.cart_id = event.cart_id
    if event.lead_id is not None:
        order.lead_id = event.lead_id
    if event.customer_id is not None:
        order.customer_id = event.customer_id
    order.sales_channel_id = event.sales_channel_id
    order.market_code = event.market_code
    order.payment_method = payload.get("payment_method")
    order.order_state = payload.get("order_state")
    order.payment_state = payload.get("payment_state")
    order.total_amount = parse_money(payload.get("total_amount"))
    order.currency = payload.get("currency")
    order.updated_at = event.occurred_at
    order.aggregate_version = event.aggregate_version
    order.last_event_occurred_at = event.occurred_at
    order.is_stub = False

    if event.visitor_id is not None:
        visitor = require_row(
            await session.get(Visitor, event.visitor_id),
            entity="visitor",
            event_type=event.event_type,
        )
        copy_attribution_snapshot(visitor, order)

    await replace_order_lines(
        session,
        order_id=order_id,
        line_items=payload.get("line_items") or [],
        currency=payload["currency"],
        source_event_type=event.event_type,
        is_paid_snapshot=False,
    )
