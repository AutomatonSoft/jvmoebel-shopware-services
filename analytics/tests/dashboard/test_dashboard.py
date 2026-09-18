from pathlib import Path

import pytest

from domains.dashboard import router as dashboard_router
from tests.reports.helpers import PERIOD, report_params

DIST_INDEX = Path(__file__).resolve().parents[2] / "dashboard" / "dist" / "index.html"


async def test_dashboard_requires_basic_auth(client) -> None:
    response = await client.get("/dashboard")
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic")


async def test_dashboard_rejects_wrong_password(client, dashboard_auth) -> None:
    user, _password = dashboard_auth
    response = await client.get("/dashboard", auth=(user, "wrong-password"))
    assert response.status_code == 401


async def test_dashboard_config_lists_shops(client, dashboard_auth) -> None:
    response = await client.get("/dashboard/config", auth=dashboard_auth)
    assert response.status_code == 200
    shops = response.json()["shops"]
    assert shops
    assert shops[0]["label"]
    assert shops[0]["id"]


async def test_read_api_accepts_dashboard_basic(
    client,
    dashboard_auth,
) -> None:
    response = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
        auth=dashboard_auth,
    )
    assert response.status_code == 200
    assert response.json()["visitors"] == 0


async def test_read_api_still_returns_json_401(client) -> None:
    response = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
    )
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "Authentication required"


async def test_empty_daily_fills_period_days(
    client,
    read_auth_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/analytics/overview/daily",
        params=PERIOD,
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [row["date"] for row in items] == ["2026-08-24"]
    assert items[0]["paid_sales"] == 0
    assert items[0]["money"] == []


async def test_daily_counts_paid_order(
    persist_event,
    load_shopware_event,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    await persist_event(load_shopware_event("order-paid"))
    response = await client.get(
        "/api/v1/analytics/overview/daily",
        params=PERIOD,
        headers=read_auth_headers,
    )
    assert response.status_code == 200
    row = response.json()["items"][0]
    assert row["orders_paid"] == 1
    assert row["paid_sales"] == 1
    assert row["money"][0]["currency"] == "EUR"


async def test_dashboard_unbuilt_returns_503(
    client,
    dashboard_auth,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(dashboard_router, "DIST_DIR", tmp_path / "missing-dist")
    response = await client.get("/dashboard/", auth=dashboard_auth)
    assert response.status_code == 503
    assert "Dashboard UI is not built" in response.text


@pytest.mark.skipif(not DIST_INDEX.is_file(), reason="dashboard dist is not built")
async def test_dashboard_serves_spa(client, dashboard_auth) -> None:
    response = await client.get("/dashboard/sources", auth=dashboard_auth)
    assert response.status_code == 200
    assert b'id="root"' in response.content
