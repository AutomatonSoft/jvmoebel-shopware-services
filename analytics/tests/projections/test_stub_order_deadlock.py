from domains.projections.models.entities import Lead, Order, Visitor


async def test_overlapping_stubs_do_not_fail(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    contact = load_shopware_event("contact-received")
    order = load_shopware_event("order-created")
    order["visitor_id"] = contact["visitor_id"]
    order["lead_id"] = contact["lead_id"]

    await persist_event(contact)
    await persist_event(order)

    visitor = await db_session.get(Visitor, contact["visitor_id"])
    lead = await db_session.get(Lead, contact["lead_id"])
    stored_order = await db_session.get(Order, order["order_id"])
    assert visitor is not None
    assert lead is not None
    assert stored_order is not None
    assert stored_order.created_event_id is not None
    assert lead.is_stub is True
