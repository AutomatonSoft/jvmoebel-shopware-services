from datetime import datetime, timezone
from decimal import Decimal

from domains.projections.models.entities import Lead, Order
from domains.projections.versioning import should_apply_entity_update

NOW = datetime(2026, 8, 24, 9, 0, tzinfo=timezone.utc)


def test_equal_aggregate_version_is_not_applied() -> None:
    assert should_apply_entity_update(
        is_stub=False,
        stored_aggregate_version=2,
        incoming_aggregate_version=2,
        stored_occurred_at=NOW,
        incoming_occurred_at=NOW,
        has_version_column=True,
    ) is False


def test_greater_aggregate_version_is_applied() -> None:
    assert should_apply_entity_update(
        is_stub=False,
        stored_aggregate_version=2,
        incoming_aggregate_version=3,
        stored_occurred_at=NOW,
        incoming_occurred_at=NOW,
        has_version_column=True,
    ) is True


def test_equal_occurred_at_is_not_applied() -> None:
    assert should_apply_entity_update(
        is_stub=False,
        stored_aggregate_version=None,
        incoming_aggregate_version=None,
        stored_occurred_at=NOW,
        incoming_occurred_at=NOW,
        has_version_column=False,
    ) is False


async def test_older_aggregate_version_is_skipped(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("lead-created")
    created["aggregate_version"] = 2
    await persist_event(created)

    older = load_shopware_event("lead-status-changed")
    older["lead_id"] = created["lead_id"]
    older["visitor_id"] = created["visitor_id"]
    older["aggregate_version"] = 1
    older["payload"] = {
        "previous_status": "new",
        "new_status": "lost",
    }
    await persist_event(older)

    lead = await db_session.get(Lead, created["lead_id"])
    assert lead is not None
    assert lead.status == "new"
    assert lead.lost_at is None
    assert lead.aggregate_version == 2


async def test_equal_aggregate_version_does_not_overwrite_order(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("order-created")
    updated = load_shopware_event("order-updated")
    updated["order_id"] = created["order_id"]
    updated["lead_id"] = created["lead_id"]
    updated["aggregate_id"] = created["order_id"]
    updated["aggregate_version"] = created["aggregate_version"]
    updated["payload"]["total_amount"] = "99.00"

    await persist_event(created)
    await persist_event(updated)

    order = await db_session.get(Order, created["order_id"])
    assert order is not None
    assert order.total_amount == Decimal("2499.00")
    assert order.aggregate_version == created["aggregate_version"]
