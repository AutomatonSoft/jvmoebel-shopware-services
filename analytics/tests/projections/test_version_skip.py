from copy import deepcopy
from uuid import uuid4

from domains.projections.models.entities import Lead


async def test_older_aggregate_version_is_skipped(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("lead-created")
    created["aggregate_version"] = 2
    await persist_event(created)

    older = load_shopware_event("lead-status-changed")
    older["lead_id"] = created["lead_id"]
    older["visitor_id"] = created["visitor_id"]
    older["aggregate_version"] = 1
    older["payload"] = {
        "previous_status": "new",
        "new_status": "lost",
    }
    await persist_event(older)

    lead = await db_session.get(Lead, created["lead_id"])
    assert lead is not None
    assert lead.status == "new"
    assert lead.lost_at is None
    assert lead.aggregate_version == 2
