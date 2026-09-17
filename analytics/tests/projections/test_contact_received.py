from domains.projections.models.facts import Contact


async def test_phone_contact_stores_call_fields(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    contact = load_shopware_event("contact-received-phone")
    await persist_event(contact)

    stored = await db_session.get(Contact, contact["contact_id"])
    assert stored is not None
    assert stored.contact_channel == "phone"
    assert stored.contact_type == "qualified_call"
    assert stored.duration_seconds == 185
    assert stored.connection_status == "answered"


async def test_form_contact_has_no_call_fields(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    contact = load_shopware_event("contact-received")
    await persist_event(contact)

    stored = await db_session.get(Contact, contact["contact_id"])
    assert stored is not None
    assert stored.contact_channel == "form"
    assert stored.duration_seconds is None
    assert stored.connection_status is None
