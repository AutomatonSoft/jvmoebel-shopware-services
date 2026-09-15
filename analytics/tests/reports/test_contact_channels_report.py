from tests.reports.helpers import http_event, report_params, uniquify_ids


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
