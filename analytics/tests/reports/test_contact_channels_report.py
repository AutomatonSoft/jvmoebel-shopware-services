from tests.reports.helpers import http_event, report_params, uniquify_ids

ORPHAN_LEAD_ID = "018f1111111111111111111111111112"


def _form_row(body: dict) -> dict:
    return next(row for row in body["items"] if row["channel"] == "form")


async def _channels(client, read_auth_headers: dict[str, str]) -> dict:
    response = await client.get(
        "/api/v1/analytics/contact-channels",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    return response.json()


async def test_contact_channels_separates_contacts_and_leads(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(http_event("contact-intent")))
    lead = load_shopware_event("lead-created")
    first = load_shopware_event("contact-received")
    first["occurred_at"] = "2026-08-24T10:00:00Z"
    second = load_shopware_event("contact-received")
    second["occurred_at"] = "2026-08-24T11:00:00Z"
    second["contact_id"] = "018f7777777777777777777777777778"
    second["aggregate_id"] = second["contact_id"]
    paid = load_shopware_event("order-paid")
    paid["occurred_at"] = "2026-08-24T11:00:00Z"
    await persist_event(lead)
    await persist_event(first)
    await persist_event(second)
    await persist_event(paid)

    response = await client.get(
        "/api/v1/analytics/contact-channels",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    items = {row["channel"]: row for row in response.json()["items"]}
    form = items["form"]
    whatsapp = items["whatsapp"]
    assert form["contacts"] == 2
    assert form["leads"] == 1
    assert form["intents"] == 0
    assert form["orders_paid"] == 1
    assert form["manual_sales"] == 0
    assert form["contact_to_lead"] == "0.5000"
    assert form["lead_to_paid_sale"] == "1.0000"
    assert form["money"][0]["currency"] == "EUR"
    assert form["money"][0]["gross"] == "2499.0000"
    assert whatsapp["intents"] == 1
    assert whatsapp["contacts"] == 0
    assert whatsapp["leads"] == 0
    assert whatsapp["contact_to_lead"] is None
    assert whatsapp["lead_to_paid_sale"] is None


async def test_contact_channels_lead_to_sale_is_unique_leads(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    lead = load_shopware_event("lead-created")
    first = load_shopware_event("order-paid")
    first["occurred_at"] = "2026-08-24T11:00:00Z"
    second = load_shopware_event("order-paid")
    second["occurred_at"] = "2026-08-24T12:00:00Z"
    second["order_id"] = "018f3333333333333333333333333334"
    second["aggregate_id"] = second["order_id"]
    await persist_event(lead)
    await persist_event(first)
    await persist_event(second)

    response = await client.get(
        "/api/v1/analytics/contact-channels",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    form = next(row for row in response.json()["items"] if row["channel"] == "form")
    assert form["leads"] == 1
    assert form["orders_paid"] == 2
    assert form["lead_to_paid_sale"] == "1.0000"


async def test_contact_to_lead_ignores_leads_without_period_contact(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    linked = load_shopware_event("lead-created")
    orphan = load_shopware_event("lead-created")
    orphan["lead_id"] = ORPHAN_LEAD_ID
    orphan["aggregate_id"] = ORPHAN_LEAD_ID
    contact = load_shopware_event("contact-received")
    contact["occurred_at"] = "2026-08-24T10:00:00Z"
    await persist_event(linked)
    await persist_event(orphan)
    await persist_event(contact)

    form = _form_row(await _channels(client, read_auth_headers))
    assert form["contacts"] == 1
    assert form["leads"] == 2
    assert form["contact_to_lead"] == "1.0000"


async def test_lead_to_paid_sale_counts_sale_after_period(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("lead-created"))
    paid = load_shopware_event("order-paid")
    paid["occurred_at"] = "2026-08-25T10:00:00Z"
    await persist_event(paid)

    form = _form_row(await _channels(client, read_auth_headers))
    assert form["leads"] == 1
    assert form["orders_paid"] == 0
    assert form["lead_to_paid_sale"] == "1.0000"


async def test_lead_to_paid_sale_counts_later_manual_sale(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("lead-created"))
    sale = load_shopware_event("manual-sale-created")
    sale["occurred_at"] = "2026-08-25T10:00:00Z"
    sale["payload"] = {**sale["payload"], "confirmed_at": "2026-08-25T10:00:00Z"}
    await persist_event(sale)

    form = _form_row(await _channels(client, read_auth_headers))
    assert form["leads"] == 1
    assert form["manual_sales"] == 0
    assert form["lead_to_paid_sale"] == "1.0000"


async def test_lead_to_paid_sale_ignores_sale_of_older_lead(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    older = load_shopware_event("lead-created")
    older["occurred_at"] = "2026-08-23T09:00:00Z"
    newer = load_shopware_event("lead-created")
    newer["lead_id"] = ORPHAN_LEAD_ID
    newer["aggregate_id"] = ORPHAN_LEAD_ID
    paid = load_shopware_event("order-paid")
    await persist_event(older)
    await persist_event(newer)
    await persist_event(paid)

    form = _form_row(await _channels(client, read_auth_headers))
    assert form["leads"] == 1
    assert form["orders_paid"] == 1
    assert form["lead_to_paid_sale"] == "0.0000"
