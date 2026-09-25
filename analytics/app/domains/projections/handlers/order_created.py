from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import copy_attribution_snapshot_if_missing
from domains.projections.exceptions import require_id, require_row
from domains.projections.locking import get_aggregate_for_update
from domains.projections.models.entities import Order, Visitor
from domains.projections.models.journal import Event
from domains.projections.order_lines import has_unpaid_lines, replace_order_lines
from domains.projections.parsing import event_payload, parse_money
from domains.projections.refund_currency import sync_refund_currency_validity
from domains.projections.versioning import (
    order_identity_values,
    overlay_attributes,
    should_apply_entity_update,
)


async def copy_order_snapshot_if_missing(
    session: AsyncSession,
    event: Event,
    order: Order,
) -> None:
    if event.visitor_id is None:
        return
    visitor = require_row(
        await session.get(Visitor, event.visitor_id),
        entity="visitor",
        event_type=event.event_type,
    )
    copy_attribution_snapshot_if_missing(visitor, order)


async def handle_order_created(
    session: AsyncSession,
    event: Event,
) -> None:
    order_id = require_id(
        event.order_id,
        field="order_id",
        event_type=event.event_type,
    )
    order = await get_aggregate_for_update(
        session,
        Order,
        order_id,
        entity="order",
        event_type=event.event_type,
    )
    if order.created_event_id is not None:
        return

    payload = event_payload(event)
    apply_state = (
        order.paid_event_id is None
        and order.cancelled_at is None
        and should_apply_entity_update(
            stored_aggregate_version=order.aggregate_version,
            incoming_aggregate_version=event.aggregate_version,
            stored_occurred_at=order.last_event_occurred_at,
            incoming_occurred_at=event.occurred_at,
            has_version_column=True,
        )
    )

    order.created_event_id = event.event_id
    order.created_at = event.occurred_at
    order.is_stub = False
    overlay_attributes(
        order,
        order_identity_values(event, payload),
        only_empty=not apply_state,
    )

    if apply_state:
        order.order_state = payload.get("order_state")
        order.payment_state = payload.get("payment_state")
        order.total_amount = parse_money(payload.get("total_amount"))
        order.updated_at = event.occurred_at
        order.aggregate_version = event.aggregate_version
        order.last_event_occurred_at = event.occurred_at
        await replace_order_lines(
            session,
            order_id=order_id,
            line_items=payload.get("line_items") or [],
            currency=payload["currency"],
            source_event_type=event.event_type,
            is_paid_snapshot=False,
        )
    elif not await has_unpaid_lines(session, order_id):
        await replace_order_lines(
            session,
            order_id=order_id,
            line_items=payload.get("line_items") or [],
            currency=payload["currency"],
            source_event_type=event.event_type,
            is_paid_snapshot=False,
        )

    await copy_order_snapshot_if_missing(session, event, order)
    await sync_refund_currency_validity(session, order)
