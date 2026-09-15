async def test_ingest_requires_auth(
    client,
    session_started_event: dict,
) -> None:
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers={"Origin": "http://test"},
    )
    assert response.status_code == 401


async def test_ingest_rejects_invalid_token(
    client,
    session_started_event: dict,
    invalid_auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers={
            **invalid_auth_headers,
            "Origin": "http://test",
        },
    )
    assert response.status_code == 401
