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


async def test_products_subtract_refund_lines(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    paid = load_shopware_event("order-paid")
    refund = load_shopware_event("refund-created")
    refund["order_id"] = paid["order_id"]
    refund["payload"]["line_items"] = [
        {
            "line_item_id": paid["payload"]["line_items"][0]["line_item_id"],
            "product_number": "SOFA-001",
            "item_type": "product",
            "quantity": 1,
            "unit_price": "500.00",
            "total_price": "500.00",
        }
    ]
    await persist_event(session_started_event)
    await persist_event(paid)
    await persist_event(refund)

    response = await client.get(
        "/api/v1/analytics/products",
        params=report_params(),
        headers=read_auth_headers,
    )
    sofa = {row["sku"]: row for row in response.json()["items"]}["SOFA-001"]
    assert sofa["money"][0]["gross"] == "2499.0000"
    assert sofa["money"][0]["refunds"] == "500.0000"
    assert sofa["money"][0]["net"] == "1999.0000"
