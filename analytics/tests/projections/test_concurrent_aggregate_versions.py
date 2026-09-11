import asyncio
from decimal import Decimal

from domains.ingestion.service import persist_validated_event
from domains.projections.models.entities import Lead, ManualSale, Order
from tests.conftest import TestSessionLocal

CONCURRENT_TIMEOUT_SECONDS = 5


async def _persist_own(body: dict) -> str:
    async with TestSessionLocal() as session:
        async with session.begin():
            return await persist_validated_event(session, body)


async def _persist_own_many(*bodies: dict) -> list[str]:
    # *bodies — события, в любом количестве
    return await asyncio.wait_for(
        # для каждого события создаётся корутина _persist_own       
        asyncio.gather(*(_persist_own(body) for body in bodies)),
        timeout=CONCURRENT_TIMEOUT_SECONDS,
    )


async def _reload(model, pk):
    async with TestSessionLocal() as session:
        return await session.get(model, pk)


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


async def test_newer_order_version_wins_when_applied_concurrently(
    persist_event,
    load_shopware_event,
) -> None:
    created = load_shopware_event("order-created")
    older = _bind_order(load_shopware_event("order-updated"), created)
    newer = _bind_order(load_shopware_event("order-updated"), created)
    older["aggregate_version"] = 4
    older["payload"]["total_amount"] = "100.00"
    newer["aggregate_version"] = 5
    newer["payload"]["total_amount"] = "200.00"

    await persist_event(created)
    await _persist_own_many(older, newer)

    order = await _reload(Order, created["order_id"])
    assert order is not None
    assert order.aggregate_version == 5
    assert order.total_amount == Decimal("200.00")
    assert order.paid_event_id is None


async def test_order_updated_cannot_overwrite_concurrent_order_paid(
    persist_event,
    load_shopware_event,
) -> None:
    created = load_shopware_event("order-created")
    updated = _bind_order(load_shopware_event("order-updated"), created)
    paid = _bind_order(load_shopware_event("order-paid"), created)
    updated["aggregate_version"] = 4
    updated["payload"]["total_amount"] = "99.00"
    paid["aggregate_version"] = 5

    await persist_event(created)
    await _persist_own_many(updated, paid)

    order = await _reload(Order, created["order_id"])
    assert order is not None
    assert order.aggregate_version == 5
    assert order.paid_event_id is not None
    assert order.paid_amount == Decimal("2499.00")


async def test_stale_order_event_is_skipped_after_newer_version(
    persist_event,
    load_shopware_event,
) -> None:
    created = load_shopware_event("order-created")
    paid = _bind_order(load_shopware_event("order-paid"), created)
    stale = _bind_order(load_shopware_event("order-updated"), created)
    paid["aggregate_version"] = 5
    stale["aggregate_version"] = 4
    stale["payload"]["total_amount"] = "99.00"

    await persist_event(created)
    await persist_event(paid)
    await persist_event(stale)

    order = await _reload(Order, created["order_id"])
    assert order is not None
    assert order.aggregate_version == 5
    assert order.paid_event_id is not None
    assert order.paid_amount == Decimal("2499.00")
    assert order.total_amount == Decimal("2499.00")


async def test_newer_lead_version_wins_when_applied_concurrently(
    persist_event,
    load_shopware_event,
) -> None:
    created = load_shopware_event("lead-created")
    older = _bind_lead(load_shopware_event("lead-status-changed"), created)
    newer = _bind_lead(load_shopware_event("lead-status-changed"), created)
    older["aggregate_version"] = 2
    older["payload"] = {
        "previous_status": "new",
        "new_status": "contacted",
    }
    newer["aggregate_version"] = 3
    newer["payload"] = {
        "previous_status": "contacted",
        "new_status": "won",
    }

    await persist_event(created)
    await _persist_own_many(older, newer)

    lead = await _reload(Lead, created["lead_id"])
    assert lead is not None
    assert lead.aggregate_version == 3
    assert lead.status == "won"
    assert lead.won_at is not None


async def test_newer_manual_sale_version_wins_when_applied_concurrently(
    persist_event,
    load_shopware_event,
) -> None:
    created = load_shopware_event("manual-sale-created")
    older = _bind_manual_sale(load_shopware_event("manual-sale-updated"), created)
    newer = _bind_manual_sale(load_shopware_event("manual-sale-updated"), created)
    older["aggregate_version"] = 2
    older["payload"]["amount"] = "1700.00"
    newer["aggregate_version"] = 3
    newer["payload"]["amount"] = "2100.00"

    await persist_event(created)
    await _persist_own_many(older, newer)

    sale = await _reload(ManualSale, created["manual_sale_id"])
    assert sale is not None
    assert sale.aggregate_version == 3
    assert sale.amount == Decimal("2100.00")


async def test_related_visitor_lead_order_events_do_not_deadlock(
    persist_event,
    load_shopware_event,
) -> None:
    created = load_shopware_event("order-created")
    lead_created = load_shopware_event("lead-created")
    _bind_lead(lead_created, created)
    paid = _bind_order(load_shopware_event("order-paid"), created)
    status = _bind_lead(load_shopware_event("lead-status-changed"), created)
    paid["aggregate_version"] = 5
    status["aggregate_version"] = 2
    status["payload"] = {
        "previous_status": "new",
        "new_status": "won",
    }

    await persist_event(lead_created)
    await persist_event(created)
    await _persist_own_many(paid, status)

    order = await _reload(Order, created["order_id"])
    lead = await _reload(Lead, created["lead_id"])
    assert order is not None
    assert lead is not None
    assert order.paid_event_id is not None
    assert order.aggregate_version == 5
    assert lead.status == "won"
    assert lead.aggregate_version == 2
