from domains.projections.models.entities import Lead
from domains.projections.models.facts import Contact


async def test_contact_received_does_not_count_as_lead(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    contact = load_shopware_event("contact-received")
    await persist_event(contact)

    lead = await db_session.get(Lead, contact["lead_id"])
    stored_contact = await db_session.get(Contact, contact["contact_id"])
    assert stored_contact is not None
    assert lead is not None
    assert lead.is_stub is True
    assert lead.event_id is None
