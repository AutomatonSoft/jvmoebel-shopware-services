from tests.reports.helpers import uniquify_ids

CUSTOMER_ID = "018f2222222222222222222222222222"


def _event_types(body: dict) -> list[str]:
    return [item["event_type"] for item in body["events"]]


async def test_customer_journey_includes_linked_visitor_session(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    linked = load_shopware_event("customer-linked")
    paid = load_shopware_event("order-paid")
    other = uniquify_ids(session_started_event, visitor=True, session=True)

    await persist_event(session_started_event)
    await persist_event(linked)
    await persist_event(paid)
    await persist_event(other)

    response = await client.get(
        f"/api/v1/analytics/customers/{CUSTOMER_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    types = _event_types(response.json())
    assert "session_started" in types
    assert "customer_linked" in types
    assert "order_paid" in types
    visitor_ids = {
        item["visitor_id"] for item in response.json()["events"]
    }
    assert session_started_event["visitor_id"] in visitor_ids
    assert other["visitor_id"] not in visitor_ids


async def test_customer_journey_includes_lead_events_without_visitor(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    contact = load_shopware_event("contact-received-direct-email")
    created = load_shopware_event("lead-created")
    created["lead_id"] = contact["lead_id"]
    created["aggregate_id"] = contact["lead_id"]
    created["customer_id"] = CUSTOMER_ID
    created.pop("visitor_id", None)
    created.pop("session_id", None)
    created.pop("cart_id", None)

    await persist_event(contact)
    await persist_event(created)

    response = await client.get(
        f"/api/v1/analytics/customers/{CUSTOMER_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    types = _event_types(response.json())
    assert "contact_received" in types
    assert "lead_created" in types
    assert all(item["visitor_id"] is None for item in response.json()["events"])


async def test_customer_journey_includes_manual_sale_before_customer_id(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    created = load_shopware_event("manual-sale-created")
    created.pop("customer_id", None)
    created.pop("visitor_id", None)
    created.pop("session_id", None)
    created.pop("cart_id", None)
    updated = load_shopware_event("manual-sale-updated")
    updated["manual_sale_id"] = created["manual_sale_id"]
    updated["aggregate_id"] = created["manual_sale_id"]
    updated["lead_id"] = created["lead_id"]
    updated["customer_id"] = CUSTOMER_ID
    updated["aggregate_version"] = 2
    updated.pop("visitor_id", None)
    updated.pop("session_id", None)
    updated.pop("cart_id", None)

    await persist_event(created)
    await persist_event(updated)

    response = await client.get(
        f"/api/v1/analytics/customers/{CUSTOMER_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    types = _event_types(response.json())
    assert "manual_sale_created" in types
    assert "manual_sale_updated" in types


async def test_customer_journey_unknown_is_404(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        f"/api/v1/analytics/customers/{'a' * 32}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 404
