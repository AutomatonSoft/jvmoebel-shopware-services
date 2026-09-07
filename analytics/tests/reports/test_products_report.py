from tests.reports.helpers import http_event, report_params, uniquify_ids


async def test_products_view_to_paid_and_line_money(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    viewed = http_event("product-viewed")
    await persist_event(session_started_event)
    await persist_event(uniquify_ids(viewed))
    await persist_event(uniquify_ids(viewed))
    await persist_event(uniquify_ids(http_event("add-to-cart")))
    await persist_event(load_shopware_event("order-created"))
    await persist_event(load_shopware_event("order-paid"))

    response = await client.get(
        "/api/v1/analytics/products",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    items = {row["sku"]: row for row in response.json()["items"]}
    sofa = items["SOFA-001"]
    assert sofa["views"] == 2
    assert sofa["cart_adds"] == 1
    assert sofa["orders_created"] == 1
    assert sofa["orders_paid"] == 1
    assert sofa["paid_quantity"] == 1
    assert sofa["view_to_paid_order"] == "0.5000"
    assert sofa["payment_methods"] == ["paypal"]
    assert sofa["money"][0]["currency"] == "EUR"
    assert sofa["money"][0]["gross"] == "2499.0000"
