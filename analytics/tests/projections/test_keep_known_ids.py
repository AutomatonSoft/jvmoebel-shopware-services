from uuid import UUID

from domains.projections.models.entities import Lead, Order


async def test_order_created_does_not_clear_known_ids(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("order-created")
    late = load_shopware_event("order-created")
    late["order_id"] = created["order_id"]
    late["aggregate_id"] = created["order_id"]
    late["aggregate_version"] = 2
    late["visitor_id"] = None
    late["session_id"] = None
    late["cart_id"] = None
    late["lead_id"] = None
    late["customer_id"] = None

    await persist_event(created)
    await persist_event(late)

    order = await db_session.get(Order, created["order_id"])
    assert order is not None
    assert order.visitor_id == UUID(created["visitor_id"])
    assert order.session_id == UUID(created["session_id"])
    assert order.cart_id == UUID(created["cart_id"])
    assert order.lead_id == created["lead_id"]
    assert order.customer_id == created["customer_id"]


async def test_lead_created_does_not_clear_known_ids(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("lead-created")
    late = load_shopware_event("lead-created")
    late["lead_id"] = created["lead_id"]
    late["aggregate_id"] = created["lead_id"]
    late["aggregate_version"] = 2
    late["visitor_id"] = None
    late["session_id"] = None
    late["customer_id"] = None

    await persist_event(created)
    await persist_event(late)

    lead = await db_session.get(Lead, created["lead_id"])
    assert lead is not None
    assert lead.visitor_id == UUID(created["visitor_id"])
    assert lead.session_id == UUID(created["session_id"])
