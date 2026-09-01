from sqlalchemy import func, select

from domains.projections.models.journal import Event


async def test_http_accepts_frontend_event(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    db_session,
) -> None:
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 1


async def test_http_rejects_shopware_type(
    client,
    ingest_headers: dict[str, str],
    shopware_order_paid_event: dict,
) -> None:
    response = await client.post(
        "/api/v1/events",
        json=shopware_order_paid_event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert "not allowed" in response.json()["detail"]


async def test_http_rejects_unknown_type(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
) -> None:
    session_started_event["event_type"] = "not_a_real_event"
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert "not allowed" in response.json()["detail"]
