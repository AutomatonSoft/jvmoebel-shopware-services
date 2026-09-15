async def test_unknown_sales_channel_id_is_rejected(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
) -> None:
    session_started_event["sales_channel_id"] = "f" * 32
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown sales_channel_id"


async def test_disallowed_origin_is_rejected(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
) -> None:
    ingest_headers["Origin"] = "https://evil.example"
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert "Origin" in response.json()["detail"]


async def test_foreign_domain_is_rejected(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
) -> None:
    session_started_event["domain"] = "www.jvmoebel.at"
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert "domain" in response.json()["detail"]


async def test_market_code_mismatch_is_rejected(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
) -> None:
    session_started_event["market_code"] = "uk"
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert "market_code" in response.json()["detail"]
