from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import copy_attribution_snapshot
from domains.projections.exceptions import require_id, require_row
from domains.projections.locking import get_aggregate_for_update
from domains.projections.models.entities import ManualSale, Visitor
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload, parse_datetime, parse_money
from domains.projections.versioning import should_apply_entity_update


async def handle_manual_sale_created(
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
    if sale.event_id is not None:
        return
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
    sale.event_id = event.event_id
    if event.visitor_id is not None:
        sale.visitor_id = event.visitor_id
    if event.lead_id is not None:
        sale.lead_id = event.lead_id
    if event.customer_id is not None:
        sale.customer_id = event.customer_id
    sale.sales_channel_id = event.sales_channel_id
    sale.market_code = event.market_code
    sale.amount = parse_money(payload.get("amount"))
    sale.currency = payload.get("currency")
    sale.reference = payload.get("reference")
    sale.status = "confirmed"
    sale.confirmed_at = parse_datetime(payload["confirmed_at"])
    sale.is_stub = False
    sale.aggregate_version = event.aggregate_version
    sale.last_event_occurred_at = event.occurred_at

    if event.visitor_id is not None:
        visitor = require_row(
            await session.get(Visitor, event.visitor_id),
            entity="visitor",
            event_type=event.event_type,
        )
        copy_attribution_snapshot(visitor, sale)
