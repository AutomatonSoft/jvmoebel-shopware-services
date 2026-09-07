from tests.reports.helpers import report_params, uniquify_ids


async def _sources(client, read_auth_headers, **params) -> list[dict]:
    response = await client.get(
        "/api/v1/analytics/sources",
        params=report_params(**params),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    return response.json()["items"]


async def test_sources_split_by_campaign(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    other = uniquify_ids(session_started_event, visitor=True, session=True)
    other["payload"] = {
        **other["payload"],
        "utm": {
            **other["payload"]["utm"],
            "utm_campaign": "later-campaign",
        },
    }
    await persist_event(session_started_event)
    await persist_event(other)

    items = await _sources(client, read_auth_headers)
    rows = {(row["source"], row["campaign"]): row for row in items}
    assert set(rows) == {
        ("google_ads", "sofas-de-2026"),
        ("google_ads", "later-campaign"),
    }
    assert rows[("google_ads", "sofas-de-2026")]["visitors"] == 1
    assert rows[("google_ads", "later-campaign")]["visitors"] == 1


async def test_sources_attribution_model_switches_bucket(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    later = uniquify_ids(session_started_event, session=True)
    later["occurred_at"] = "2026-08-24T12:00:00Z"
    later["payload"] = {
        **later["payload"],
        "utm": {},
        "click_ids": {},
        "referrer": "https://example.com/blog",
    }
    await persist_event(session_started_event)
    await persist_event(later)

    first = await _sources(
        client,
        read_auth_headers,
        attribution_model="first_touch",
    )
    last = await _sources(
        client,
        read_auth_headers,
        attribution_model="last_non_direct",
    )
    assert [(row["source"], row["campaign"]) for row in first] == [
        ("google_ads", "sofas-de-2026")
    ]
    assert [(row["source"], row["campaign"]) for row in last] == [("referral", None)]


async def test_sources_contacts_conversions_and_money(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    lead = load_shopware_event("lead-created")
    lead["occurred_at"] = "2026-08-24T10:00:00Z"
    first = load_shopware_event("contact-received")
    first["occurred_at"] = "2026-08-24T10:00:00Z"
    second = load_shopware_event("contact-received")
    second["occurred_at"] = "2026-08-24T11:00:00Z"
    second["contact_id"] = "018f7777777777777777777777777778"
    second["aggregate_id"] = second["contact_id"]
    created = load_shopware_event("order-created")
    paid = load_shopware_event("order-paid")
    paid["occurred_at"] = "2026-08-24T11:00:00Z"
    await persist_event(lead)
    await persist_event(first)
    await persist_event(second)
    await persist_event(created)
    await persist_event(paid)

    items = await _sources(client, read_auth_headers)
    assert len(items) == 1
    row = items[0]
    assert row["source"] == "google_ads"
    assert row["campaign"] == "sofas-de-2026"
    assert row["sessions"] == 1
    assert row["contacts"] == 2
    assert row["leads"] == 1
    assert row["orders_created"] == 1
    assert row["orders_paid"] == 1
    assert row["manual_sales"] == 0
    assert row["session_to_lead"] == "1.0000"
    assert row["session_to_paid_sale"] == "1.0000"
    assert row["lead_to_paid_sale"] == "1.0000"
    assert row["first_visit_to_lead_seconds"] == "3600"
    assert row["first_visit_to_paid_sale_seconds"] == "7200"
    assert row["money"][0]["currency"] == "EUR"
    assert row["money"][0]["gross"] == "2499.0000"


async def test_sources_mixed_currency_is_not_summed(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    usd = load_shopware_event("order-paid")
    usd["order_id"] = "018f3333333333333333333333333334"
    usd["aggregate_id"] = usd["order_id"]
    usd["payload"] = {
        **usd["payload"],
        "currency": "USD",
        "total_amount": "100.0000",
        "order_number": "100246",
        "line_items": [
            {
                **usd["payload"]["line_items"][0],
                "line_item_id": "018f4444444444444444444444444445",
                "total_price": "100.0000",
                "unit_price": "100.0000",
            }
        ],
    }
    await persist_event(session_started_event)
    await persist_event(load_shopware_event("order-paid"))
    await persist_event(usd)

    items = await _sources(client, read_auth_headers)
    money = {row["currency"]: row for row in items[0]["money"]}
    assert set(money) == {"EUR", "USD"}
    assert money["EUR"]["gross"] == "2499.0000"
    assert money["USD"]["gross"] == "100.0000"
