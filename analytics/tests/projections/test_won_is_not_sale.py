from domains.projections.models.entities import Lead
from domains.projections.models.entities import Order


async def test_won_does_not_create_sale(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("lead-created")
    await persist_event(created)

    won = load_shopware_event("lead-status-changed")
    won["lead_id"] = created["lead_id"]
    won["visitor_id"] = created["visitor_id"]
    won["order_id"] = "018f3333333333333333333333333333"
    won["aggregate_version"] = 2
    won["payload"] = {
        "previous_status": "new",
        "new_status": "won",
    }
    await persist_event(won)

    lead = await db_session.get(Lead, created["lead_id"])
    order = await db_session.get(Order, won["order_id"])
    assert lead is not None
    assert lead.status == "won"
    assert lead.won_at is not None
    assert order is not None
    assert order.is_stub is True
    assert order.paid_event_id is None
    assert order.created_event_id is None
