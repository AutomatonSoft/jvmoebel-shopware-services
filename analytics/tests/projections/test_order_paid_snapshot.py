from decimal import Decimal

from sqlalchemy import select

from domains.projections.models.entities import Order
from domains.projections.models.facts import OrderLine


async def test_order_updated_does_not_overwrite_paid_snapshot(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("order-created")
    paid = load_shopware_event("order-paid")
    updated = load_shopware_event("order-updated")
    paid["order_id"] = created["order_id"]
    paid["lead_id"] = created["lead_id"]
    paid["aggregate_version"] = 2
    updated["order_id"] = created["order_id"]
    updated["lead_id"] = created["lead_id"]
    updated["aggregate_version"] = 3
    updated["payload"]["total_amount"] = "99.00"

    await persist_event(created)
    await persist_event(paid)
    await persist_event(updated)

    order = await db_session.get(Order, created["order_id"])
    lines = list(
        (
            await db_session.scalars(
                select(OrderLine).where(OrderLine.order_id == created["order_id"])
            )
        ).all()
    )
    assert order is not None
    assert order.paid_event_id is not None
    assert order.paid_amount == Decimal("2499.00")
    paid_lines = [line for line in lines if line.is_paid_snapshot]
    unpaid_lines = [line for line in lines if not line.is_paid_snapshot]
    assert paid_lines
    assert unpaid_lines
    assert all(line.total_price == Decimal("2499.00") for line in paid_lines)
