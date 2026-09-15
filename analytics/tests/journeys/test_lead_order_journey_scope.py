import json
from pathlib import Path

from tests.reports.helpers import uniquify_ids

LEAD_ID = "018f1111111111111111111111111111"
ORDER_ID = "018f3333333333333333333333333333"
UNKNOWN_ID = "a" * 32

HTTP_EXAMPLES = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "http"
    / "examples"
    / "valid"
)


def _event_types(body: dict) -> list[str]:
    return [item["event_type"] for item in body["events"]]


def _http_event(stem: str) -> dict:
    return json.loads((HTTP_EXAMPLES / f"{stem}.json").read_text(encoding="utf-8"))


async def test_lead_journey_includes_linked_visitor_session(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    created = load_shopware_event("lead-created")
    other = uniquify_ids(session_started_event, visitor=True, session=True)

    await persist_event(session_started_event)
    await persist_event(created)
    await persist_event(other)

    response = await client.get(
        f"/api/v1/analytics/leads/{LEAD_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    types = _event_types(response.json())
    assert "session_started" in types
    assert "lead_created" in types
    visitor_ids = {item["visitor_id"] for item in response.json()["events"]}
    assert session_started_event["visitor_id"] in visitor_ids
    assert other["visitor_id"] not in visitor_ids


async def test_lead_journey_includes_order_and_refund_without_lead_id(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    created = load_shopware_event("lead-created")
    paid = load_shopware_event("order-paid")
    refund = load_shopware_event("refund-created")
    refund.pop("lead_id", None)

    await persist_event(created)
    await persist_event(paid)
    await persist_event(refund)

    response = await client.get(
        f"/api/v1/analytics/leads/{LEAD_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    types = _event_types(response.json())
    assert "lead_created" in types
    assert "order_paid" in types
    assert "refund_created" in types


async def test_lead_journey_without_visitor_keeps_contact_and_lead(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    contact = load_shopware_event("contact-received-direct-email")
    created = load_shopware_event("lead-created")
    created["lead_id"] = contact["lead_id"]
    created["aggregate_id"] = contact["lead_id"]
    created.pop("visitor_id", None)
    created.pop("session_id", None)
    created.pop("cart_id", None)

    await persist_event(contact)
    await persist_event(created)

    response = await client.get(
        f"/api/v1/analytics/leads/{LEAD_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    types = _event_types(response.json())
    assert "contact_received" in types
    assert "lead_created" in types
    assert all(item["visitor_id"] is None for item in response.json()["events"])


async def test_lead_journey_unknown_is_404(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        f"/api/v1/analytics/leads/{UNKNOWN_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 404


async def test_order_journey_includes_visitor_cart_and_refund(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    viewed = uniquify_ids(_http_event("product-viewed"))
    checkout = uniquify_ids(_http_event("checkout-started"))
    paid = load_shopware_event("order-paid")
    refund = load_shopware_event("refund-created")
    other = uniquify_ids(session_started_event, visitor=True, session=True)

    await persist_event(session_started_event)
    await persist_event(viewed)
    await persist_event(checkout)
    await persist_event(paid)
    await persist_event(refund)
    await persist_event(other)

    response = await client.get(
        f"/api/v1/analytics/orders/{ORDER_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    types = _event_types(response.json())
    assert "session_started" in types
    assert "product_viewed" in types
    assert "checkout_started" in types
    assert "order_paid" in types
    assert "refund_created" in types
    visitor_ids = {item["visitor_id"] for item in response.json()["events"]}
    assert session_started_event["visitor_id"] in visitor_ids
    assert other["visitor_id"] not in visitor_ids


async def test_order_journey_unknown_is_404(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        f"/api/v1/analytics/orders/{UNKNOWN_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 404
