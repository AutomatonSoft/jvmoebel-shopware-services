from tests.reports.helpers import report_params


async def test_mixed_currency_is_not_summed(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    eur = load_shopware_event("order-paid")
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
    await persist_event(eur)
    await persist_event(usd)

    response = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
        headers=read_auth_headers,
    )
    body = response.json()
    assert response.status_code == 200
    assert body["orders_paid"] == 2
    money = {row["currency"]: row for row in body["money"]}
    assert set(money) == {"EUR", "USD"}
    assert money["EUR"]["gross"] == "2499.0000"
    assert money["USD"]["gross"] == "100.0000"
    assert money["EUR"]["net"] == "2499.0000"
    assert money["USD"]["net"] == "100.0000"

    eur_only = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(currency="EUR"),
        headers=read_auth_headers,
    )
    eur_money = eur_only.json()["money"]
    assert len(eur_money) == 1
    assert eur_money[0]["currency"] == "EUR"
    assert eur_money[0]["gross"] == "2499.0000"
