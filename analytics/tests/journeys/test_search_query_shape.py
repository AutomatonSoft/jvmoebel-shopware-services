import json
from pathlib import Path
from uuid import uuid4

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"

VISITOR_ID = "550e8400-e29b-41d4-a716-446655440000"
SESSION_ID = "9b1de427-512a-482e-a2bf-66d1f6de06e3"
LEAD_ID = "018f1111111111111111111111111111"
ORDER_ID = "018f3333333333333333333333333333"
CONTACT_ID = "018f7777777777777777777777777777"


def _http_event(stem: str) -> dict:
    path = CONTRACTS_DIR / "http" / "examples" / "valid" / f"{stem}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _hit_ids(body: dict, entity_type: str) -> set[str]:
    return {
        item["id"]
        for item in body["items"]
        if item["entity_type"] == entity_type
    }


async def test_search_requires_read_key(client) -> None:
    response = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": VISITOR_ID},
    )
    assert response.status_code == 401


async def test_search_blank_query_is_400(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "   "},
        headers=read_auth_headers,
    )
    assert response.status_code == 400


async def test_search_uuid_v4_matches_visitor_and_session(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)

    visitor = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": VISITOR_ID},
        headers=read_auth_headers,
    )
    session = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": SESSION_ID},
        headers=read_auth_headers,
    )
    assert visitor.status_code == 200
    assert session.status_code == 200
    assert _hit_ids(visitor.json(), "visitor") == {VISITOR_ID}
    assert _hit_ids(session.json(), "session") == {SESSION_ID}


async def test_search_hex_matches_lead_order_contact(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(load_shopware_event("contact-received"))
    await persist_event(load_shopware_event("order-paid"))

    lead = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": LEAD_ID},
        headers=read_auth_headers,
    )
    order = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": ORDER_ID},
        headers=read_auth_headers,
    )
    contact = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": CONTACT_ID},
        headers=read_auth_headers,
    )
    assert _hit_ids(lead.json(), "lead") == {LEAD_ID}
    assert _hit_ids(order.json(), "order") == {ORDER_ID}
    assert _hit_ids(contact.json(), "contact") == {CONTACT_ID}


async def test_search_text_matches_order_number_gclid_tracking_campaign(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("order-paid"))
    await persist_event(load_shopware_event("contact-received"))

    order_number = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "100245"},
        headers=read_auth_headers,
    )
    gclid = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "Cj0KCQjw-example"},
        headers=read_auth_headers,
    )
    tracking = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "trk-8f27a1"},
        headers=read_auth_headers,
    )
    campaign = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "sofas-de-2026"},
        headers=read_auth_headers,
    )
    assert _hit_ids(order_number.json(), "order") == {ORDER_ID}
    assert _hit_ids(gclid.json(), "visitor") == {VISITOR_ID}
    assert _hit_ids(tracking.json(), "contact") == {CONTACT_ID}
    assert _hit_ids(campaign.json(), "visitor") == {VISITOR_ID}


async def test_search_text_matches_contact_channel(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(load_shopware_event("contact-received"))
    await persist_event(_http_event("contact-intent"))

    form = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "form"},
        headers=read_auth_headers,
    )
    form_upper = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "FORM"},
        headers=read_auth_headers,
    )
    whatsapp = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "whatsapp"},
        headers=read_auth_headers,
    )
    phone = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": "phone"},
        headers=read_auth_headers,
    )

    assert form.status_code == 200
    assert _hit_ids(form.json(), "contact") == {CONTACT_ID}
    assert _hit_ids(form.json(), "lead") == {LEAD_ID}
    assert _hit_ids(form_upper.json(), "contact") == {CONTACT_ID}
    assert _hit_ids(form_upper.json(), "lead") == {LEAD_ID}
    assert _hit_ids(whatsapp.json(), "visitor") == {VISITOR_ID}
    assert phone.json()["items"] == []


async def test_visitor_journey_returns_payload(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)

    response = await client.get(
        f"/api/v1/analytics/visitors/{VISITOR_ID}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    events = response.json()["events"]
    assert events[0]["event_type"] == "session_started"
    assert events[0]["payload"]["utm"]["utm_campaign"] == "sofas-de-2026"


async def test_unknown_visitor_journey_is_404(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        f"/api/v1/analytics/visitors/{uuid4()}/journey",
        headers=read_auth_headers,
    )
    assert response.status_code == 404
