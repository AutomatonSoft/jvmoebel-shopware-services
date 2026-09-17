from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import copy_attribution_snapshot_if_missing
from domains.projections.exceptions import require_id, require_row
from domains.projections.locking import get_aggregate_for_update
from domains.projections.models.entities import ManualSale, Visitor
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload, parse_datetime, parse_money
from domains.projections.versioning import overlay_attributes, should_apply_entity_update


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

    payload = event_payload(event)
    apply_state = (
        sale.cancelled_at is None
        and should_apply_entity_update(
            stored_aggregate_version=sale.aggregate_version,
            incoming_aggregate_version=event.aggregate_version,
            stored_occurred_at=sale.last_event_occurred_at,
            incoming_occurred_at=event.occurred_at,
            has_version_column=True,
        )
    )

    sale.event_id = event.event_id
    sale.confirmed_at = parse_datetime(payload["confirmed_at"])
    sale.is_stub = False
    overlay_attributes(
        sale,
        {
            "visitor_id": event.visitor_id,
            "lead_id": event.lead_id,
            "customer_id": event.customer_id,
            "sales_channel_id": event.sales_channel_id,
            "market_code": event.market_code,
            "amount": parse_money(payload.get("amount")),
            "currency": payload.get("currency"),
            "reference": payload.get("reference"),
        },
        only_empty=not apply_state,
    )

    if apply_state:
        sale.status = "confirmed"
        sale.aggregate_version = event.aggregate_version
        sale.last_event_occurred_at = event.occurred_at

    if event.visitor_id is not None:
        visitor = require_row(
            await session.get(Visitor, event.visitor_id),
            entity="visitor",
            event_type=event.event_type,
        )
        copy_attribution_snapshot_if_missing(visitor, sale)
