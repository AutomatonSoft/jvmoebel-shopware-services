import pytest

from core.config import settings
from tests.reports.helpers import report_params, uniquify_ids


async def test_sales_channel_filter_does_not_mix_markets(
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
    event_b = uniquify_ids(session_started_event, visitor=True, session=True)
    event_b["sales_channel_id"] = channel_b.id
    event_b["market_code"] = channel_b.market_code
    await persist_event(event_a)
    await persist_event(event_b)

    filtered_a = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(sales_channel=channel_a.id),
        headers=read_auth_headers,
    )
    filtered_b = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(sales_channel=channel_b.id),
        headers=read_auth_headers,
    )
    combined = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
        headers=read_auth_headers,
    )

    assert filtered_a.status_code == 200
    assert filtered_a.json()["visitors"] == 1
    assert filtered_a.json()["sessions"] == 1
    assert filtered_b.json()["visitors"] == 1
    assert filtered_b.json()["sessions"] == 1
    assert combined.json()["visitors"] == 2
    assert combined.json()["sessions"] == 2
