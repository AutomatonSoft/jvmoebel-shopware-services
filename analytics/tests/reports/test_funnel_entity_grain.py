import json
from pathlib import Path

from tests.reports.helpers import report_params, uniquify_ids

HTTP_EXAMPLES = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "http"
    / "examples"
    / "valid"
)

ECOMMERCE_KEYS = (
    "session",
    "product_view",
    "add_to_cart",
    "checkout_started",
    "order_created",
    "order_paid",
)
LEAD_KEYS = (
    "session",
    "contact_intent",
    "contact_received",
    "lead_created",
    "lead_won",
    "paid_sale",
)


def _http_event(stem: str) -> dict:
    return json.loads((HTTP_EXAMPLES / f"{stem}.json").read_text(encoding="utf-8"))


def _steps_by_key(steps: list[dict]) -> dict[str, dict]:
    return {step["key"]: step for step in steps}


async def _funnel(client, read_auth_headers: dict[str, str]) -> dict:
    response = await client.get(
        "/api/v1/analytics/funnel",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    return response.json()


async def test_empty_funnel_has_null_conversions(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    body = await _funnel(client, read_auth_headers)
    ecommerce = _steps_by_key(body["ecommerce"])
    lead = _steps_by_key(body["lead"])
    assert list(ecommerce) == list(ECOMMERCE_KEYS)
    assert list(lead) == list(LEAD_KEYS)
    for step in [*ecommerce.values(), *lead.values()]:
        assert step["count"] == 0
        assert step["conversion_from_previous"] is None


async def test_funnel_counts_visitors_not_product_view_rows(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    viewed = _http_event("product-viewed")
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(viewed))
    await persist_event(uniquify_ids(viewed))

    body = await _funnel(client, read_auth_headers)
    ecommerce = _steps_by_key(body["ecommerce"])
    assert ecommerce["session"]["count"] == 1
    assert ecommerce["product_view"]["count"] == 1
    assert ecommerce["product_view"]["conversion_from_previous"] == "1.0000"


async def test_ecommerce_funnel_adjacent_conversions(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(_http_event("product-viewed")))
    await persist_event(uniquify_ids(_http_event("add-to-cart")))
    await persist_event(uniquify_ids(_http_event("checkout-started")))
    await persist_event(load_shopware_event("order-created"))
    await persist_event(load_shopware_event("order-paid"))

    ecommerce = _steps_by_key((await _funnel(client, read_auth_headers))["ecommerce"])
    assert [ecommerce[key]["count"] for key in ECOMMERCE_KEYS] == [1, 1, 1, 1, 1, 1]
    assert ecommerce["session"]["conversion_from_previous"] is None
    assert ecommerce["product_view"]["conversion_from_previous"] == "1.0000"
    assert ecommerce["add_to_cart"]["conversion_from_previous"] == "1.0000"
    assert ecommerce["checkout_started"]["conversion_from_previous"] == "1.0000"
    assert ecommerce["order_created"]["conversion_from_previous"] == "1.0000"
    assert ecommerce["order_paid"]["conversion_from_previous"] == "1.0000"


async def test_lead_funnel_separates_intents_contacts_and_won(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    intent = _http_event("contact-intent")
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(intent))
    await persist_event(uniquify_ids(intent))
    await persist_event(load_shopware_event("lead-created"))
    first = load_shopware_event("contact-received")
    first["occurred_at"] = "2026-08-24T10:00:00Z"
    second = load_shopware_event("contact-received")
    second["occurred_at"] = "2026-08-24T11:00:00Z"
    second["contact_id"] = "018f7777777777777777777777777778"
    second["aggregate_id"] = second["contact_id"]
    await persist_event(first)
    await persist_event(second)
    won = load_shopware_event("lead-status-changed")
    won["occurred_at"] = "2026-08-24T12:00:00Z"
    won["aggregate_version"] = 2
    won["payload"] = {"previous_status": "new", "new_status": "won"}
    await persist_event(won)

    lead = _steps_by_key((await _funnel(client, read_auth_headers))["lead"])
    assert lead["session"]["count"] == 1
    assert lead["contact_intent"]["count"] == 1
    assert lead["contact_received"]["count"] == 2
    assert lead["lead_created"]["count"] == 1
    assert lead["lead_won"]["count"] == 1
    assert lead["paid_sale"]["count"] == 0
    assert lead["contact_intent"]["conversion_from_previous"] == "1.0000"
    assert lead["contact_received"]["conversion_from_previous"] == "2.0000"
    assert lead["lead_created"]["conversion_from_previous"] == "0.5000"
    assert lead["lead_won"]["conversion_from_previous"] == "1.0000"
    assert lead["paid_sale"]["conversion_from_previous"] == "0.0000"


async def test_lead_won_is_not_paid_sale(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("lead-created"))
    won = load_shopware_event("lead-status-changed")
    won["occurred_at"] = "2026-08-24T12:00:00Z"
    won["aggregate_version"] = 2
    won["payload"] = {"previous_status": "new", "new_status": "won"}
    await persist_event(won)

    body = await _funnel(client, read_auth_headers)
    lead = _steps_by_key(body["lead"])
    ecommerce = _steps_by_key(body["ecommerce"])
    assert lead["lead_won"]["count"] == 1
    assert lead["paid_sale"]["count"] == 0
    assert ecommerce["order_paid"]["count"] == 0


async def test_paid_sale_includes_order_paid_and_manual_sale(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("order-paid"))
    await persist_event(load_shopware_event("manual-sale-created"))

    body = await _funnel(client, read_auth_headers)
    lead = _steps_by_key(body["lead"])
    ecommerce = _steps_by_key(body["ecommerce"])
    assert ecommerce["order_paid"]["count"] == 1
    assert lead["paid_sale"]["count"] == 2
    assert lead["paid_sale"]["conversion_from_previous"] is None
