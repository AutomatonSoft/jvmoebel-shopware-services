from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from domains.projections.models.entities import Lead, ManualSale, Order
from domains.projections.models.facts import LeadStatusHistory, OrderLine


def _bind_order(target: dict, source: dict) -> dict:
    target["order_id"] = source["order_id"]
    target["lead_id"] = source["lead_id"]
    target["visitor_id"] = source["visitor_id"]
    target["session_id"] = source["session_id"]
    target["aggregate_id"] = source["order_id"]
    return target


def _bind_lead(target: dict, source: dict) -> dict:
    target["lead_id"] = source["lead_id"]
    target["visitor_id"] = source["visitor_id"]
    target["session_id"] = source["session_id"]
    target["aggregate_id"] = source["lead_id"]
    return target


def _bind_manual_sale(target: dict, source: dict) -> dict:
    target["manual_sale_id"] = source["manual_sale_id"]
    target["lead_id"] = source["lead_id"]
    target["visitor_id"] = source["visitor_id"]
    target["aggregate_id"] = source["manual_sale_id"]
    return target


async def test_order_paid_before_created_keeps_creation_and_payment(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("order-created")
    paid = _bind_order(load_shopware_event("order-paid"), created)
    paid["aggregate_version"] = 2
    paid["occurred_at"] = "2026-08-24T10:00:00Z"
    created["occurred_at"] = "2026-08-24T09:00:00Z"

    await persist_event(paid)
    await persist_event(created)

    order = await db_session.get(Order, created["order_id"])
    lines = list(
        (
            await db_session.scalars(
                select(OrderLine).where(OrderLine.order_id == created["order_id"])
            )
        ).all()
    )
    assert order is not None
    assert order.created_event_id == UUID(created["event_id"])
    assert order.paid_event_id == UUID(paid["event_id"])
    assert order.paid_amount == Decimal("2499.00")
    assert order.payment_state == "paid"
    assert order.created_at is not None
    assert order.created_at.isoformat().startswith("2026-08-24T09:00:00")
    unpaid = [line for line in lines if not line.is_paid_snapshot]
    paid_lines = [line for line in lines if line.is_paid_snapshot]
    assert unpaid
    assert paid_lines


async def test_order_updated_before_created_keeps_newer_state(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("order-created")
    updated = _bind_order(load_shopware_event("order-updated"), created)
    updated["aggregate_version"] = 2
    updated["payload"]["total_amount"] = "99.00"

    await persist_event(updated)
    await persist_event(created)

    order = await db_session.get(Order, created["order_id"])
    assert order is not None
    assert order.created_event_id == UUID(created["event_id"])
    assert order.total_amount == Decimal("99.00")
    assert order.aggregate_version == 2


async def test_order_cancelled_before_created_keeps_cancellation(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("order-created")
    cancelled = _bind_order(load_shopware_event("order-cancelled"), created)
    cancelled["aggregate_version"] = 2
    cancelled["occurred_at"] = "2026-08-24T11:00:00Z"

    await persist_event(cancelled)
    await persist_event(created)

    order = await db_session.get(Order, created["order_id"])
    assert order is not None
    assert order.created_event_id == UUID(created["event_id"])
    assert order.cancelled_at is not None
    assert order.order_state == "cancelled"


async def test_lead_status_changed_before_created_does_not_reset_status(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("lead-created")
    won = _bind_lead(load_shopware_event("lead-status-changed"), created)
    won["aggregate_version"] = 2
    won["occurred_at"] = "2026-08-24T10:00:00Z"
    won["payload"] = {
        "previous_status": "new",
        "new_status": "won",
    }

    await persist_event(won)
    await persist_event(created)

    lead = await db_session.get(Lead, created["lead_id"])
    assert lead is not None
    assert lead.event_id == UUID(created["event_id"])
    assert lead.status == "won"
    assert lead.won_at is not None
    assert lead.contact_channel == "form"
    assert lead.created_at is not None
    assert lead.created_at.isoformat().startswith("2026-08-24T09:00:00")


async def test_lead_status_changes_out_of_order_keep_latest_status(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("lead-created")
    contacted = _bind_lead(load_shopware_event("lead-status-changed"), created)
    won = _bind_lead(load_shopware_event("lead-status-changed"), created)
    contacted["aggregate_version"] = 2
    contacted["occurred_at"] = "2026-08-24T10:00:00Z"
    contacted["payload"] = {
        "previous_status": "new",
        "new_status": "contacted",
    }
    won["aggregate_version"] = 3
    won["occurred_at"] = "2026-08-24T11:00:00Z"
    won["payload"] = {
        "previous_status": "contacted",
        "new_status": "won",
    }

    await persist_event(created)
    await persist_event(won)
    await persist_event(contacted)

    lead = await db_session.get(Lead, created["lead_id"])
    history = await db_session.scalar(
        select(func.count()).select_from(LeadStatusHistory)
    )
    assert lead is not None
    assert lead.status == "won"
    assert lead.aggregate_version == 3
    assert history == 1


async def test_manual_sale_updated_before_created_keeps_newer_amount(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("manual-sale-created")
    updated = _bind_manual_sale(load_shopware_event("manual-sale-updated"), created)
    updated["aggregate_version"] = 2
    updated["payload"]["amount"] = "1900.00"

    await persist_event(updated)
    await persist_event(created)

    sale = await db_session.get(ManualSale, created["manual_sale_id"])
    assert sale is not None
    assert sale.event_id == UUID(created["event_id"])
    assert sale.amount == Decimal("1900.00")
    assert sale.status == "confirmed"
    assert sale.confirmed_at is not None
