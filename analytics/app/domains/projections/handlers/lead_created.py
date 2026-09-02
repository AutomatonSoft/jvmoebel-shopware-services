from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import copy_attribution_snapshot
from domains.projections.exceptions import require_id, require_row
from domains.projections.models.entities import Lead, Visitor
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload
from domains.projections.versioning import should_apply_entity_update


async def handle_lead_created(
    session: AsyncSession,
    event: Event,
) -> None:
    lead_id = require_id(
        event.lead_id,
        field="lead_id",
        event_type=event.event_type,
    )
    lead = require_row(
        await session.get(Lead, lead_id),
        entity="lead",
        event_type=event.event_type,
    )
    if not should_apply_entity_update(
        is_stub=lead.is_stub,
        stored_aggregate_version=lead.aggregate_version,
        incoming_aggregate_version=event.aggregate_version,
        stored_occurred_at=lead.last_event_occurred_at,
        incoming_occurred_at=event.occurred_at,
        has_version_column=True,
    ):
        return

    payload = event_payload(event)
    lead.event_id = event.event_id
    lead.visitor_id = event.visitor_id
    lead.session_id = event.session_id
    lead.sales_channel_id = event.sales_channel_id
    lead.market_code = event.market_code
    lead.status = payload.get("status")
    lead.contact_channel = payload.get("contact_channel")
    lead.contact_type = payload.get("contact_type")
    lead.provider = payload.get("provider")
    lead.customer_id = event.customer_id
    lead.created_at = event.occurred_at
    lead.is_stub = False
    lead.aggregate_version = event.aggregate_version
    lead.last_event_occurred_at = event.occurred_at

    if event.visitor_id is not None:
        visitor = require_row(
            await session.get(Visitor, event.visitor_id),
            entity="visitor",
            event_type=event.event_type,
        )
        copy_attribution_snapshot(visitor, lead)
