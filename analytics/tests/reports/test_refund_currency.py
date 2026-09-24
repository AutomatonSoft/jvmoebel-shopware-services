import pytest
from sqlalchemy import func, select

from domains.projections.exceptions import ProjectionInvariantError
from domains.projections.models.facts import Refund
from domains.projections.models.journal import Event
from domains.projections.refund_currency import CURRENCY_MISMATCH
from tests.reports.helpers import report_params


async def _overview(client, read_auth_headers: dict[str, str]) -> dict:
    response = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    return response.json()


def _money(body: dict) -> dict[str, dict]:
    return {row["currency"]: row for row in body["money"]}


def _usd_refund(load_shopware_event, order_id: str) -> dict:
    refund = load_shopware_event("refund-created")
    refund["order_id"] = order_id
    refund["payload"]["currency"] = "USD"
    return refund


async def test_refund_before_order_paid_matches_currency(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    paid = load_shopware_event("order-paid")
    refund = load_shopware_event("refund-created")
    refund["order_id"] = paid["order_id"]
    await persist_event(refund)
    await persist_event(paid)

    money = _money(await _overview(client, read_auth_headers))
    assert set(money) == {"EUR"}
    assert money["EUR"]["gross"] == "2499.0000"
    assert money["EUR"]["refunds"] == "500.0000"
    assert money["EUR"]["net"] == "1999.0000"


async def test_matching_refund_currency_subtracts_from_net(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    paid = load_shopware_event("order-paid")
    refund = load_shopware_event("refund-created")
    refund["order_id"] = paid["order_id"]
    await persist_event(paid)
    await persist_event(refund)

    money = _money(await _overview(client, read_auth_headers))
    assert set(money) == {"EUR"}
    assert money["EUR"]["gross"] == "2499.0000"
    assert money["EUR"]["refunds"] == "500.0000"
    assert money["EUR"]["net"] == "1999.0000"


async def test_mismatched_refund_after_order_is_rejected(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
    db_session,
) -> None:
    paid = load_shopware_event("order-paid")
    refund = _usd_refund(load_shopware_event, paid["order_id"])
    await persist_event(paid)

    with pytest.raises(ProjectionInvariantError, match="currency"):
        await persist_event(refund)

    stored = await db_session.get(Refund, refund["refund_id"])
    assert stored is None
    events = await db_session.scalar(
        select(func.count())
        .select_from(Event)
        .where(Event.event_type == "refund_created")
    )
    assert events == 0

    money = _money(await _overview(client, read_auth_headers))
    assert money["EUR"]["gross"] == "2499.0000"
    assert money["EUR"]["refunds"] == "0.0000"
    assert money["EUR"]["net"] == "2499.0000"


async def test_mismatched_refund_before_order_is_marked_invalid(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
    db_session,
) -> None:
    paid = load_shopware_event("order-paid")
    refund = _usd_refund(load_shopware_event, paid["order_id"])
    await persist_event(refund)
    await persist_event(paid)

    stored = await db_session.get(Refund, refund["refund_id"])
    assert stored is not None
    assert stored.currency == "USD"
    assert stored.invalid_reason == CURRENCY_MISMATCH

    money = _money(await _overview(client, read_auth_headers))
    assert set(money) == {"EUR"}
    assert money["EUR"]["gross"] == "2499.0000"
    assert money["EUR"]["refunds"] == "0.0000"
    assert money["EUR"]["net"] == "2499.0000"
