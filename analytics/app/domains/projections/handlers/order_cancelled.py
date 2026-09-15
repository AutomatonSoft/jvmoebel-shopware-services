from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id
from domains.projections.locking import get_aggregate_for_update
from domains.projections.models.entities import Order
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload
from domains.projections.versioning import should_apply_entity_update


async def handle_order_cancelled(
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
    order.order_state = payload.get("order_state")
    order.payment_state = payload.get("payment_state")
    order.cancelled_at = event.occurred_at
    order.aggregate_version = event.aggregate_version
    order.last_event_occurred_at = event.occurred_at
    order.is_stub = False
