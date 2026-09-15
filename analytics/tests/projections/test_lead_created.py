from uuid import UUID

from domains.projections.models.entities import Lead


async def test_repeat_lead_created_does_not_overwrite(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("lead-created")
    repeat = load_shopware_event("lead-created")
    repeat["lead_id"] = created["lead_id"]
    repeat["aggregate_id"] = created["lead_id"]
    repeat["aggregate_version"] = 2
    repeat["occurred_at"] = "2026-08-24T12:00:00Z"
    repeat["payload"] = {
        **repeat["payload"],
        "status": "won",
        "contact_channel": "phone",
    }

    await persist_event(created)
    await persist_event(repeat)

    lead = await db_session.get(Lead, created["lead_id"])
    assert lead is not None
    assert lead.event_id == UUID(created["event_id"])
    assert lead.status == "new"
    assert lead.contact_channel == "form"
    assert lead.created_at is not None
    assert lead.created_at.isoformat().startswith("2026-08-24T09:00:00")
