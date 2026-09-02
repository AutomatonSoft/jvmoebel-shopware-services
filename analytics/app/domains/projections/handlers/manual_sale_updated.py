from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id, require_row
from domains.projections.models.entities import ManualSale
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload, parse_money
from domains.projections.versioning import should_apply_entity_update


async def handle_manual_sale_updated(
    session: AsyncSession,
    event: Event,
) -> None:
    manual_sale_id = require_id(
        event.manual_sale_id,
        field="manual_sale_id",
        event_type=event.event_type,
    )
    sale = require_row(
        await session.get(ManualSale, manual_sale_id),
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
    sale.amount = parse_money(payload.get("amount"))
    sale.currency = payload.get("currency")
    sale.status = payload.get("status")
    if payload.get("reference") is not None:
        sale.reference = payload.get("reference")
    if event.visitor_id is not None:
        sale.visitor_id = event.visitor_id
    if event.lead_id is not None:
        sale.lead_id = event.lead_id
    if event.customer_id is not None:
        sale.customer_id = event.customer_id
    sale.sales_channel_id = event.sales_channel_id
    sale.market_code = event.market_code
    sale.is_stub = False
    sale.aggregate_version = event.aggregate_version
    sale.last_event_occurred_at = event.occurred_at
