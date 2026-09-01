from sqlalchemy import func, select

from domains.projections.models.journal import Event


async def test_repeat_event_id_is_duplicate(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    db_session,
) -> None:
    first = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    second = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )

    assert first.status_code == 200
    assert first.json() == {"status": "accepted"}
    assert second.status_code == 200
    assert second.json() == {"status": "duplicate"}

    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 1
