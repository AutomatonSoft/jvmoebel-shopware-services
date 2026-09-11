from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id
from domains.projections.locking import get_aggregate_for_update
from domains.projections.models.entities import ManualSale
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload, parse_datetime
from domains.projections.versioning import should_apply_entity_update


async def handle_manual_sale_cancelled(
    session: AsyncSession,
    event: Event,
) -> None:
    manual_sale_id = require_id(
        event.manual_sale_id,
        field="manual_sale_id",
        event_type=event.event_type,
    )
    sale = await get_aggregate_for_update(
        session,
        ManualSale,
        manual_sale_id,
        entity="manual_sale",
        event_type=event.event_type,
    )
    if not should_apply_entity_update(
        is_stub=sale.is_stub,
        stored_aggregate_version=sale.aggregate_version,
        incoming_aggregate_version=event.aggregate_version,
        stored_occurred_at=sale.last_event_occurred_at,
        incoming_occurred_at=event.occurred_at,
        has_version_column=True,
    ):
        return

    payload = event_payload(event)
    sale.status = "cancelled"
    sale.cancelled_at = parse_datetime(payload["cancelled_at"])
    sale.aggregate_version = event.aggregate_version
    sale.last_event_occurred_at = event.occurred_at
    sale.is_stub = False
