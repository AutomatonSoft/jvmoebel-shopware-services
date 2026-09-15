from tests.reports.helpers import http_event, report_params, uniquify_ids


async def test_payment_methods_selected_to_paid_and_money(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    shown = http_event("payment-methods-shown")
    selected = http_event("payment-method-selected")
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(shown))
    await persist_event(uniquify_ids(shown))
    await persist_event(uniquify_ids(selected))
    await persist_event(load_shopware_event("order-created"))
    await persist_event(load_shopware_event("order-paid"))

    response = await client.get(
        "/api/v1/analytics/payment-methods",
        params=report_params(),
        headers=read_auth_headers,
    )
    overview = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    items = {row["payment_method"]: row for row in response.json()["items"]}
    paypal = items["paypal"]
    assert overview.json()["sessions"] == 1
    assert paypal["shown"] == 1
    assert paypal["selected"] == 1
    assert paypal["selected_rate"] == "1.0000"
    assert paypal["orders_created"] == 1
    assert paypal["orders_paid"] == 1
    assert paypal["selected_to_paid"] == "1.0000"
    assert paypal["money"][0]["currency"] == "EUR"
    assert paypal["money"][0]["gross"] == "2499.0000"
    assert paypal["money"][0]["aov"] == "2499.0000"
