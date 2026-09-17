from tests.reports.helpers import PERIOD, report_params


async def test_dashboard_requires_basic_auth(client) -> None:
    response = await client.get("/dashboard")
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic")
    assert "text/html" in response.headers["content-type"]
    assert "Authentication required" in response.text


async def test_dashboard_rejects_wrong_password(client, dashboard_auth) -> None:
    user, _password = dashboard_auth
    response = await client.get("/dashboard", auth=(user, "wrong-password"))
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Basic")


async def test_read_api_still_returns_json_401(client) -> None:
    response = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
    )
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "Authentication required"


async def test_empty_overview_html(client, dashboard_auth) -> None:
    response = await client.get("/dashboard", params=PERIOD, auth=dashboard_auth)
    assert response.status_code == 200
    assert "Overview" in response.text
    assert ">0<" in response.text
    assert "No data" in response.text


async def test_overview_shows_session(
    persist_event,
    session_started_event: dict,
    client,
    dashboard_auth,
) -> None:
    await persist_event(session_started_event)
    response = await client.get("/dashboard", params=PERIOD, auth=dashboard_auth)
    assert response.status_code == 200
    assert ">1<" in response.text


async def test_invalid_period_is_html_400(client, dashboard_auth) -> None:
    response = await client.get(
        "/dashboard",
        params={
            "period_from": "2026-08-25T00:00:00",
            "period_to": "2026-08-24T00:00:00",
        },
        auth=dashboard_auth,
    )
    assert response.status_code == 400
    assert "text/html" in response.headers["content-type"]
    assert "period_from must be" in response.text


async def test_invalid_query_is_html_422(client, dashboard_auth) -> None:
    response = await client.get(
        "/dashboard",
        params={"period_from": "yesterday", "period_to": "2026-08-24T00:00:00"},
        auth=dashboard_auth,
    )
    assert response.status_code == 422
    assert "Invalid query parameter" in response.text


async def test_funnel_and_sources_empty(client, dashboard_auth) -> None:
    funnel = await client.get("/dashboard/funnel", params=PERIOD, auth=dashboard_auth)
    sources = await client.get("/dashboard/sources", params=PERIOD, auth=dashboard_auth)
    assert funnel.status_code == 200
    assert sources.status_code == 200
    assert "No data" in funnel.text
    assert "No data" in sources.text


async def test_journey_search_empty_query(client, dashboard_auth) -> None:
    response = await client.get("/dashboard/journey", auth=dashboard_auth)
    assert response.status_code == 200
    assert "No data" not in response.text


async def test_journey_search_and_detail(
    persist_event,
    session_started_event: dict,
    client,
    dashboard_auth,
) -> None:
    await persist_event(session_started_event)
    visitor_id = session_started_event["visitor_id"]
    search = await client.get(
        "/dashboard/journey",
        params={"q": visitor_id, **PERIOD},
        auth=dashboard_auth,
    )
    assert search.status_code == 200
    assert visitor_id in search.text
    assert f"/dashboard/journey/visitor/{visitor_id}" in search.text

    detail = await client.get(
        f"/dashboard/journey/visitor/{visitor_id}",
        params=PERIOD,
        auth=dashboard_auth,
    )
    assert detail.status_code == 200
    assert "session_started" in detail.text


async def test_unknown_journey_is_html_404(client, dashboard_auth) -> None:
    response = await client.get(
        "/dashboard/journey/visitor/00000000-0000-4000-8000-000000000001",
        auth=dashboard_auth,
    )
    assert response.status_code == 404
    assert "Journey not found" in response.text
