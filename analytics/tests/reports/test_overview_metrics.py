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


def _http_event(stem: str) -> dict:
    return json.loads((HTTP_EXAMPLES / f"{stem}.json").read_text(encoding="utf-8"))


async def _overview(client, read_auth_headers: dict[str, str]) -> dict:
    response = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    return response.json()


async def test_empty_overview_has_null_rates(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    body = await _overview(client, read_auth_headers)
    assert body["visitors"] == 0
    assert body["sessions"] == 0
    assert body["product_views"] == 0
    assert body["cart_adds"] == 0
    assert body["checkouts"] == 0
    assert body["contacts"] == 0
    assert body["leads"] == 0
    assert body["orders_created"] == 0
    assert body["orders_paid"] == 0
    assert body["manual_sales"] == 0
    assert body["session_to_lead"] is None
    assert body["session_to_paid_sale"] is None
    assert body["lead_to_paid_sale"] is None
    assert body["checkout_to_paid_order"] is None
    assert body["first_visit_to_lead_seconds"] is None
    assert body["first_visit_to_paid_sale_seconds"] is None


async def test_overview_counts_product_view_rows_not_visitors(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    viewed = _http_event("product-viewed")
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(viewed))
    await persist_event(uniquify_ids(viewed))

    body = await _overview(client, read_auth_headers)
    assert body["visitors"] == 1
    assert body["product_views"] == 2


async def test_overview_counts_contacts_separately_from_leads(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("lead-created"))
    first = load_shopware_event("contact-received")
    first["occurred_at"] = "2026-08-24T10:00:00Z"
    second = load_shopware_event("contact-received")
    second["occurred_at"] = "2026-08-24T11:00:00Z"
    second["contact_id"] = "018f7777777777777777777777777778"
    second["aggregate_id"] = second["contact_id"]
    await persist_event(first)
    await persist_event(second)

    body = await _overview(client, read_auth_headers)
    assert body["contacts"] == 2
    assert body["leads"] == 1


async def test_cancelled_manual_sale_is_not_counted(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    created = load_shopware_event("manual-sale-created")
    cancelled = load_shopware_event("manual-sale-cancelled")
    cancelled["manual_sale_id"] = created["manual_sale_id"]
    cancelled["aggregate_id"] = created["manual_sale_id"]
    cancelled["aggregate_version"] = 2
    await persist_event(session_started_event)
    await persist_event(created)
    await persist_event(cancelled)

    body = await _overview(client, read_auth_headers)
    assert body["manual_sales"] == 0


async def test_overview_conversions_and_times(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(_http_event("checkout-started")))
    lead = load_shopware_event("lead-created")
    lead["occurred_at"] = "2026-08-24T10:00:00Z"
    paid = load_shopware_event("order-paid")
    paid["occurred_at"] = "2026-08-24T11:00:00Z"
    await persist_event(lead)
    await persist_event(paid)

    body = await _overview(client, read_auth_headers)
    assert body["sessions"] == 1
    assert body["checkouts"] == 1
    assert body["leads"] == 1
    assert body["orders_paid"] == 1
    assert body["manual_sales"] == 0
    assert body["session_to_lead"] == "1.0000"
    assert body["session_to_paid_sale"] == "1.0000"
    assert body["lead_to_paid_sale"] == "1.0000"
    assert body["checkout_to_paid_order"] == "1.0000"
    assert body["first_visit_to_lead_seconds"] == "3600"
    assert body["first_visit_to_paid_sale_seconds"] == "7200"


async def test_checkout_to_paid_order_ignores_manual_sale(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(_http_event("checkout-started")))
    await persist_event(load_shopware_event("lead-created"))
    await persist_event(load_shopware_event("manual-sale-created"))

    body = await _overview(client, read_auth_headers)
    assert body["orders_paid"] == 0
    assert body["manual_sales"] == 1
    assert body["session_to_paid_sale"] == "1.0000"
    assert body["lead_to_paid_sale"] == "1.0000"
    assert body["checkout_to_paid_order"] == "0.0000"


async def test_lead_to_paid_sale_ignores_ecommerce_paid(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    paid = load_shopware_event("order-paid")
    paid["lead_id"] = None
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("lead-created"))
    await persist_event(paid)

    body = await _overview(client, read_auth_headers)
    assert body["leads"] == 1
    assert body["orders_paid"] == 1
    assert body["session_to_paid_sale"] == "1.0000"
    assert body["lead_to_paid_sale"] == "0.0000"


async def test_channel_filter_counts_only_matching_leads(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("lead-created"))
    whatsapp = load_shopware_event("lead-created")
    whatsapp["lead_id"] = "018f1111111111111111111111111112"
    whatsapp["aggregate_id"] = whatsapp["lead_id"]
    whatsapp["payload"] = {**whatsapp["payload"], "contact_channel": "whatsapp"}
    await persist_event(whatsapp)

    all_leads = await _overview(client, read_auth_headers)
    filtered = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(channel="whatsapp"),
        headers=read_auth_headers,
    )
    funnel = await client.get(
        "/api/v1/analytics/funnel",
        params=report_params(channel="whatsapp"),
        headers=read_auth_headers,
    )
    lead_steps = {step["key"]: step for step in funnel.json()["lead"]}
    assert all_leads["leads"] == 2
    assert filtered.status_code == 200
    assert filtered.json()["leads"] == 1
    assert funnel.status_code == 200
    assert lead_steps["lead_created"]["count"] == 1


async def test_overview_time_skips_lead_without_visitor(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    created = load_shopware_event("lead-created")
    created.pop("visitor_id", None)
    created.pop("session_id", None)
    created.pop("cart_id", None)
    await persist_event(created)

    body = await _overview(client, read_auth_headers)
    assert body["leads"] == 1
    assert body["first_visit_to_lead_seconds"] is None
    assert body["first_visit_to_paid_sale_seconds"] is None
