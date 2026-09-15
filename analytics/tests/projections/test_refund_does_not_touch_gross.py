from decimal import Decimal

from domains.projections.models.entities import Order
from domains.projections.models.facts import Refund


async def test_refund_does_not_change_paid_amount(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    paid = load_shopware_event("order-paid")
    refund = load_shopware_event("refund-created")
    refund["order_id"] = paid["order_id"]
    await persist_event(paid)
    await persist_event(refund)

    order = await db_session.get(Order, paid["order_id"])
    stored_refund = await db_session.get(Refund, refund["refund_id"])
    assert order is not None
    assert stored_refund is not None
    assert order.paid_amount == Decimal("2499.00")
    assert stored_refund.refund_amount == Decimal("500.00")
