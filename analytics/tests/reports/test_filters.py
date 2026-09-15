from tests.reports.helpers import (
    ALLOWED_CHANNEL,
    UNKNOWN_CHANNEL,
    comparison_params,
    report_params,
    uniquify_ids,
)


async def test_reports_require_read_key(client) -> None:
    response = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
    )
    assert response.status_code == 401


async def test_reports_reject_ingest_key(
    client,
    ingest_auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
        headers=ingest_auth_headers,
    )
    assert response.status_code == 401


async def test_unknown_sales_channel_is_empty(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    empty = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(sales_channel=UNKNOWN_CHANNEL),
        headers=read_auth_headers,
    )
    matched = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(sales_channel=ALLOWED_CHANNEL),
        headers=read_auth_headers,
    )
    assert empty.status_code == 200
    assert empty.json()["visitors"] == 0
    assert empty.json()["sessions"] == 0
    assert matched.json()["visitors"] == 1
    assert matched.json()["sessions"] == 1


async def test_source_filter_excludes_other_source(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    other = uniquify_ids(session_started_event, visitor=True, session=True)
    other["payload"] = {
        **other["payload"],
        "utm": {},
        "click_ids": {},
        "referrer": "https://example.com/blog",
    }
    await persist_event(other)

    google = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(source="google_ads"),
        headers=read_auth_headers,
    )
    referral = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(source="referral"),
        headers=read_auth_headers,
    )
    assert google.json()["visitors"] == 1
    assert google.json()["sessions"] == 1
    assert referral.json()["visitors"] == 1
    assert referral.json()["sessions"] == 1


REPORT_PATHS = (
    "/api/v1/analytics/overview",
    "/api/v1/analytics/funnel",
    "/api/v1/analytics/sources",
    "/api/v1/analytics/contact-channels",
    "/api/v1/analytics/products",
    "/api/v1/analytics/payment-methods",
    "/api/v1/analytics/period-comparison",
)


async def test_all_report_endpoints_return_200(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    for path in REPORT_PATHS:
        params = (
            comparison_params()
            if path.endswith("/period-comparison")
            else report_params()
        )
        response = await client.get(
            path,
            params=params,
            headers=read_auth_headers,
        )
        assert response.status_code == 200, path
