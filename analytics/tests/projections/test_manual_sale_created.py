from decimal import Decimal

from domains.projections.models.entities import ManualSale


async def test_repeat_manual_sale_created_does_not_overwrite_amount(
    persist_event,
    load_shopware_event,
    db_session,
) -> None:
    created = load_shopware_event("manual-sale-created")
    repeat = load_shopware_event("manual-sale-created")
    repeat["manual_sale_id"] = created["manual_sale_id"]
    repeat["aggregate_id"] = created["manual_sale_id"]
    repeat["aggregate_version"] = 2
    repeat["payload"]["amount"] = "1.00"

    await persist_event(created)
    await persist_event(repeat)

    sale = await db_session.get(ManualSale, created["manual_sale_id"])
    assert sale is not None
    assert sale.amount == Decimal("1800.00")
    assert sale.event_id is not None
