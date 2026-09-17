from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import copy_attribution_snapshot_if_missing
from domains.projections.exceptions import require_id, require_row
from domains.projections.locking import get_aggregate_for_update
from domains.projections.models.entities import Lead, Visitor
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload
from domains.projections.versioning import overlay_attributes, should_apply_entity_update


async def handle_lead_created(
    session: AsyncSession,
    event: Event,
) -> None:
    lead_id = require_id(
        event.lead_id,
        field="lead_id",
        event_type=event.event_type,
    )
    lead = await get_aggregate_for_update(
        session,
        Lead,
        lead_id,
        entity="lead",
        event_type=event.event_type,
    )
    if lead.event_id is not None:
        return

    payload = event_payload(event)
    apply_state = should_apply_entity_update(
        stored_aggregate_version=lead.aggregate_version,
        incoming_aggregate_version=event.aggregate_version,
        stored_occurred_at=lead.last_event_occurred_at,
        incoming_occurred_at=event.occurred_at,
        has_version_column=True,
    )

    lead.event_id = event.event_id
    lead.created_at = event.occurred_at
    lead.is_stub = False
    overlay_attributes(
        lead,
        {
            "visitor_id": event.visitor_id,
            "session_id": event.session_id,
            "sales_channel_id": event.sales_channel_id,
            "market_code": event.market_code,
            "contact_channel": payload.get("contact_channel"),
            "contact_type": payload.get("contact_type"),
            "provider": payload.get("provider"),
            "customer_id": event.customer_id,
        },
        only_empty=not apply_state,
    )

    if apply_state:
        lead.status = payload.get("status")
        lead.aggregate_version = event.aggregate_version
        lead.last_event_occurred_at = event.occurred_at

    if event.visitor_id is not None:
        visitor = require_row(
            await session.get(Visitor, event.visitor_id),
            entity="visitor",
            event_type=event.event_type,
        )
        copy_attribution_snapshot_if_missing(visitor, lead)
