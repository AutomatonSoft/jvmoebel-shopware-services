from tests.reports.helpers import comparison_params, http_event, uniquify_ids


def _shift_to_compare_day(event: dict) -> dict:
    shifted = uniquify_ids(event, visitor=True, session=True)
    shifted["occurred_at"] = "2026-08-17T09:00:00Z"
    return shifted


async def test_period_comparison_requires_compare_range(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/analytics/period-comparison",
        params=comparison_params(),
        headers=read_auth_headers,
    )
    missing = await client.get(
        "/api/v1/analytics/period-comparison",
        params={
            "period_from": "2026-08-24T00:00:00Z",
            "period_to": "2026-08-24T23:59:59Z",
        },
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    assert missing.status_code == 400
    assert missing.json()["detail"] == "compare_from and compare_to are required"


async def test_event_only_in_current_period(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    response = await client.get(
        "/api/v1/analytics/period-comparison",
        params=comparison_params(),
        headers=read_auth_headers,
    )
    body = response.json()
    assert response.status_code == 200
    assert body["current"]["visitors"] == 1
    assert body["current"]["sessions"] == 1
    assert body["previous"]["visitors"] == 0
    assert body["previous"]["sessions"] == 0
    assert body["delta"]["visitors"] == {"abs": 1, "pct": None}
    assert body["delta"]["sessions"] == {"abs": 1, "pct": None}


async def test_visitor_pct_uses_compare_period_as_base(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(_shift_to_compare_day(session_started_event))
    await persist_event(session_started_event)
    await persist_event(
        uniquify_ids(session_started_event, visitor=True, session=True)
    )

    response = await client.get(
        "/api/v1/analytics/period-comparison",
        params=comparison_params(),
        headers=read_auth_headers,
    )
    body = response.json()
    assert body["previous"]["visitors"] == 1
    assert body["current"]["visitors"] == 2
    assert body["delta"]["visitors"] == {"abs": 1, "pct": "1.0000"}


async def test_money_delta_is_per_currency(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(load_shopware_event("order-paid"))

    response = await client.get(
        "/api/v1/analytics/period-comparison",
        params=comparison_params(),
        headers=read_auth_headers,
    )
    body = response.json()
    money = {row["currency"]: row for row in body["delta"]["money"]}
    assert set(money) == {"EUR"}
    assert money["EUR"]["gross"] == {"abs": "2499.0000", "pct": None}
    assert money["EUR"]["net"] == {"abs": "2499.0000", "pct": None}


async def test_payment_method_filter_applies_to_both_periods(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    current_shown = uniquify_ids(http_event("payment-methods-shown"))
    previous_shown = _shift_to_compare_day(http_event("payment-methods-shown"))
    previous_shown["payload"] = {"methods": ["paypal"]}
    await persist_event(session_started_event)
    await persist_event(current_shown)
    await persist_event(previous_shown)

    response = await client.get(
        "/api/v1/analytics/period-comparison",
        params=comparison_params(payment_method="paypal"),
        headers=read_auth_headers,
    )
    body = response.json()
    current_methods = {
        row["payment_method"] for row in body["payment_methods"]["current"]
    }
    previous_methods = {
        row["payment_method"] for row in body["payment_methods"]["previous"]
    }
    delta_methods = {
        row["payment_method"] for row in body["payment_methods"]["delta"]
    }
    assert current_methods == {"paypal"}
    assert previous_methods == {"paypal"}
    assert delta_methods == {"paypal"}
    assert body["payment_methods"]["delta"][0]["shown"] == {
        "abs": 0,
        "pct": "0.0000",
    }
