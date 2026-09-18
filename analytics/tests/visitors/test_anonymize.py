from uuid import UUID, uuid4

from domains.projections.models.entities import Lead, Order, Session, Visitor
from domains.projections.models.facts import AttributionTouch
from domains.projections.models.journal import Event

VISITOR_ID = "550e8400-e29b-41d4-a716-446655440000"
SESSION_ID = "9b1de427-512a-482e-a2bf-66d1f6de06e3"
GCLID = "Cj0KCQjw-example"
ANONYMIZE_PATH = f"/api/v1/analytics/visitors/{VISITOR_ID}/anonymize"


def _payload(event: Event) -> dict:
    payload = event.body.get("payload")
    if isinstance(payload, dict):
        return payload
    return {}


async def test_anonymize_requires_auth(client) -> None:
    response = await client.post(ANONYMIZE_PATH)
    assert response.status_code == 401


async def test_anonymize_rejects_dashboard_basic(client, dashboard_auth) -> None:
    response = await client.post(ANONYMIZE_PATH, auth=dashboard_auth)
    assert response.status_code == 401


async def test_anonymize_rejects_read_key(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    response = await client.post(ANONYMIZE_PATH, headers=read_auth_headers)
    assert response.status_code == 401


async def test_unknown_visitor_anonymize_is_404(
    client,
    admin_auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        f"/api/v1/analytics/visitors/{uuid4()}/anonymize",
        headers=admin_auth_headers,
    )
    assert response.status_code == 404


async def test_anonymize_redacts_identifiers_and_keeps_entities(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    admin_auth_headers: dict[str, str],
    db_session,
) -> None:
    await persist_event(session_started_event)
    created = load_shopware_event("lead-created")
    created["visitor_id"] = session_started_event["visitor_id"]
    created["session_id"] = session_started_event["session_id"]
    await persist_event(created)
    paid = load_shopware_event("order-paid")
    await persist_event(paid)

    response = await client.post(ANONYMIZE_PATH, headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "anonymized"}

    db_session.expire_all()
    visitor = await db_session.get(Visitor, UUID(VISITOR_ID))
    session_row = await db_session.get(Session, UUID(SESSION_ID))
    lead = await db_session.get(Lead, created["lead_id"])
    order = await db_session.get(Order, paid["order_id"])
    event = await db_session.get(
        Event,
        UUID(session_started_event["event_id"]),
    )
    touch = await db_session.get(
        AttributionTouch,
        UUID(session_started_event["event_id"]),
    )

    assert visitor is not None
    assert visitor.anonymized_at is not None
    assert visitor.first_touch_gclid is None
    assert visitor.first_touch_utm_campaign is None
    assert visitor.first_touch_landing_page is None
    assert visitor.first_touch_referrer is None
    assert visitor.first_touch_source == "google_ads"
    assert visitor.first_touch_campaign == "sofas-de-2026"
    assert visitor.first_touch_sales_channel_id == (
        session_started_event["sales_channel_id"]
    )

    assert session_row is not None
    assert session_row.gclid is None
    assert session_row.utm_campaign is None
    assert session_row.landing_page is None
    assert session_row.referrer is None
    assert session_row.source == "google_ads"

    assert touch is not None
    assert touch.gclid is None
    assert touch.utm_campaign is None
    assert touch.landing_page is None
    assert touch.source == "google_ads"
    assert touch.campaign == "sofas-de-2026"

    assert lead is not None
    assert lead.attr_first_touch_gclid is None
    assert lead.attr_first_touch_utm_campaign is None
    assert lead.attr_first_touch_source == "google_ads"
    assert lead.visitor_id == UUID(VISITOR_ID)

    assert order is not None
    assert order.attr_first_touch_gclid is None
    assert order.total_amount is not None
    assert order.visitor_id == UUID(VISITOR_ID)

    assert event is not None
    payload = _payload(event)
    assert "click_ids" not in payload
    assert "utm" not in payload
    assert "landing_page" not in payload
    assert "referrer" not in payload
    assert "device" not in payload
    assert event.body.get("consent") == session_started_event["consent"]


async def test_anonymize_is_idempotent(
    persist_event,
    session_started_event: dict,
    client,
    admin_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    first = await client.post(ANONYMIZE_PATH, headers=admin_auth_headers)
    second = await client.post(ANONYMIZE_PATH, headers=admin_auth_headers)
    assert first.json() == {"status": "anonymized"}
    assert second.json() == {"status": "already_anonymized"}


async def test_search_by_gclid_fails_after_anonymize(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    before = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": GCLID},
        headers=read_auth_headers,
    )
    assert before.status_code == 200
    assert before.json()["items"]

    await client.post(ANONYMIZE_PATH, headers=admin_auth_headers)

    after = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": GCLID},
        headers=read_auth_headers,
    )
    uuid_hit = await client.get(
        "/api/v1/analytics/journey/search",
        params={"q": VISITOR_ID},
        headers=read_auth_headers,
    )
    assert after.status_code == 200
    assert after.json()["items"] == []
    assert uuid_hit.status_code == 200
    assert uuid_hit.json()["items"]


async def test_session_started_after_anonymize_does_not_restore_click_ids(
    persist_event,
    session_started_event: dict,
    unique_event,
    client,
    admin_auth_headers: dict[str, str],
    db_session,
) -> None:
    await persist_event(session_started_event)
    await client.post(ANONYMIZE_PATH, headers=admin_auth_headers)

    later = unique_event(session_started_event)
    later["session_id"] = str(uuid4())
    later["occurred_at"] = "2026-08-25T09:00:00Z"
    await persist_event(later)

    db_session.expire_all()
    visitor = await db_session.get(Visitor, UUID(VISITOR_ID))
    session_row = await db_session.get(Session, UUID(later["session_id"]))
    event = await db_session.get(Event, UUID(later["event_id"]))

    assert visitor is not None
    assert visitor.anonymized_at is not None
    assert visitor.first_touch_gclid is None
    assert visitor.first_touch_source == "google_ads"
    assert session_row is not None
    assert session_row.gclid is None
    assert session_row.landing_page is None
    assert event is not None
    assert "click_ids" not in _payload(event)
