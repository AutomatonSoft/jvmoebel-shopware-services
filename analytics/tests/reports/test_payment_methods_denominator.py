import json
from pathlib import Path
from uuid import uuid4

from tests.reports.helpers import report_params, uniquify_ids

EXAMPLES = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "http"
    / "examples"
    / "valid"
)


async def test_repeated_shown_on_same_checkout_counts_once(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    shown = json.loads(
        (EXAMPLES / "payment-methods-shown.json").read_text(encoding="utf-8")
    )
    selected = json.loads(
        (EXAMPLES / "payment-method-selected.json").read_text(encoding="utf-8")
    )

    await persist_event(session_started_event)
    await persist_event(uniquify_ids(shown))
    await persist_event(uniquify_ids(shown))
    await persist_event(uniquify_ids(selected))

    response = await client.get(
        "/api/v1/analytics/payment-methods",
        params=report_params(),
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    items = {row["payment_method"]: row for row in response.json()["items"]}
    paypal = items["paypal"]
    assert paypal["shown"] == 1
    assert paypal["selected"] == 1
    assert paypal["selected_rate"] == "1.0000"


async def test_selected_rate_uses_checkouts_not_sessions(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    shown = json.loads(
        (EXAMPLES / "payment-methods-shown.json").read_text(encoding="utf-8")
    )
    selected = json.loads(
        (EXAMPLES / "payment-method-selected.json").read_text(encoding="utf-8")
    )
    first_shown = uniquify_ids(shown)
    second_shown = uniquify_ids(shown)
    second_shown["cart_id"] = str(uuid4())
    chosen = uniquify_ids(selected)
    chosen["cart_id"] = first_shown["cart_id"]

    await persist_event(session_started_event)
    await persist_event(first_shown)
    await persist_event(second_shown)
    await persist_event(chosen)

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
    sessions = overview.json()["sessions"]
    assert sessions == 1
    assert paypal["shown"] == 2
    assert paypal["selected"] == 1
    assert paypal["selected_rate"] == "0.5000"
    assert paypal["shown"] != sessions
