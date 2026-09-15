import pytest

from core.config import settings
from tests.reports.helpers import http_event, report_params, uniquify_ids


async def test_market_filter_splits_web_facts(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    if len(settings.sales_channels) < 2:
        pytest.skip("Need at least two configured sales channels")

    channel_a, channel_b = settings.sales_channels[:2]
    event_a = uniquify_ids(session_started_event, visitor=True, session=True)
    event_a["sales_channel_id"] = channel_a.id
    event_a["market_code"] = channel_a.market_code
    view_a = uniquify_ids(http_event("product-viewed"), visitor=True, session=True)
    view_a["visitor_id"] = event_a["visitor_id"]
    view_a["session_id"] = event_a["session_id"]
    view_a["sales_channel_id"] = channel_a.id
    view_a["market_code"] = channel_a.market_code

    event_b = uniquify_ids(session_started_event, visitor=True, session=True)
    event_b["sales_channel_id"] = channel_b.id
    event_b["market_code"] = channel_b.market_code
    view_b = uniquify_ids(http_event("product-viewed"), visitor=True, session=True)
    view_b["visitor_id"] = event_b["visitor_id"]
    view_b["session_id"] = event_b["session_id"]
    view_b["sales_channel_id"] = channel_b.id
    view_b["market_code"] = channel_b.market_code

    await persist_event(event_a)
    await persist_event(view_a)
    await persist_event(event_b)
    await persist_event(view_b)

    filtered_a = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(market=channel_a.market_code),
        headers=read_auth_headers,
    )
    filtered_b = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(market=channel_b.market_code),
        headers=read_auth_headers,
    )
    funnel_a = await client.get(
        "/api/v1/analytics/funnel",
        params=report_params(market=channel_a.market_code),
        headers=read_auth_headers,
    )
    products_a = await client.get(
        "/api/v1/analytics/products",
        params=report_params(market=channel_a.market_code),
        headers=read_auth_headers,
    )
    product_view = next(
        step["count"]
        for step in funnel_a.json()["ecommerce"]
        if step["key"] == "product_view"
    )
    assert filtered_a.status_code == 200
    assert filtered_a.json()["product_views"] == 1
    assert filtered_b.json()["product_views"] == 1
    assert product_view == 1
    assert products_a.json()["items"][0]["views"] == 1
