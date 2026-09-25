from tests.reports.helpers import uniquify_ids


async def test_session_journey_uses_backend_traffic_source(
    persist_event,
    session_started_event: dict,
    client,
    read_auth_headers: dict[str, str],
) -> None:
    seo = uniquify_ids(session_started_event, visitor=True, session=True)
    seo["payload"] = {
        **seo["payload"],
        "utm": {},
        "click_ids": {},
        "referrer": "https://www.google.com/",
    }
    direct = uniquify_ids(session_started_event, visitor=True, session=True)
    direct["payload"] = {
        **direct["payload"],
        "utm": {},
        "click_ids": {},
        "referrer": None,
    }
    await persist_event(session_started_event)
    await persist_event(seo)
    await persist_event(direct)

    ads_response = await client.get(
        f"/api/v1/analytics/visitors/{session_started_event['visitor_id']}/journey",
        headers=read_auth_headers,
    )
    seo_response = await client.get(
        f"/api/v1/analytics/visitors/{seo['visitor_id']}/journey",
        headers=read_auth_headers,
    )
    direct_response = await client.get(
        f"/api/v1/analytics/visitors/{direct['visitor_id']}/journey",
        headers=read_auth_headers,
    )

    ads_session = next(
        item
        for item in ads_response.json()["events"]
        if item["event_type"] == "session_started"
    )
    seo_session = next(
        item
        for item in seo_response.json()["events"]
        if item["event_type"] == "session_started"
    )
    direct_session = next(
        item
        for item in direct_response.json()["events"]
        if item["event_type"] == "session_started"
    )
    assert ads_session["source"] == "nextjs"
    assert ads_session["traffic_source"] == "google_ads"
    assert seo_session["traffic_source"] == "seo"
    assert direct_session["traffic_source"] == "direct"
