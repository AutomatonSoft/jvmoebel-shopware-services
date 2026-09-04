import json
from pathlib import Path

from tests.reports.helpers import report_params, uniquify_ids

PRODUCT_VIEWED = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "http"
    / "examples"
    / "valid"
    / "product-viewed.json"
)


async def test_funnel_counts_visitors_not_product_view_rows(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(session_started_event)
    viewed = json.loads(PRODUCT_VIEWED.read_text(encoding="utf-8"))
    first = uniquify_ids(viewed)
    first["visitor_id"] = session_started_event["visitor_id"]
    first["session_id"] = session_started_event["session_id"]
    second = uniquify_ids(viewed)
    second["visitor_id"] = session_started_event["visitor_id"]
    second["session_id"] = session_started_event["session_id"]
    await persist_event(first)
    await persist_event(second)

    response = await client.get(
        "/api/v1/analytics/funnel",
        params=report_params(),
        headers=read_auth_headers,
    )
    body = response.json()
    assert response.status_code == 200
    assert body["visitors"] == 1
    assert body["sessions"] == 1
    assert body["product_viewers"] == 1
