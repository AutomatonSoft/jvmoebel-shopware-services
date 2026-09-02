from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import require_id, require_row
from domains.projections.models.entities import Lead
from domains.projections.models.facts import LeadStatusHistory
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload
from domains.projections.versioning import should_apply_entity_update


async def handle_lead_status_changed(
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

    payload = event_payload(event)
    session.add(
        LeadStatusHistory(
            event_id=event.event_id,
            lead_id=lead_id,
            previous_status=payload["previous_status"],
            new_status=payload["new_status"],
            order_id=event.order_id,
            manual_sale_id=event.manual_sale_id,
            occurred_at=event.occurred_at,
        )
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

    new_status = payload["new_status"]
    lead.status = new_status
    lead.aggregate_version = event.aggregate_version
    lead.last_event_occurred_at = event.occurred_at
    if event.visitor_id is not None:
        lead.visitor_id = event.visitor_id
    if event.customer_id is not None:
        lead.customer_id = event.customer_id
    if new_status == "won":
        lead.won_at = event.occurred_at
    if new_status == "lost":
        lead.lost_at = event.occurred_at
