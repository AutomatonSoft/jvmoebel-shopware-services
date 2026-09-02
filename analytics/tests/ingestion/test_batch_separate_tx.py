from copy import deepcopy
from uuid import uuid4

from sqlalchemy import func, select

from domains.projections.models.journal import Event


async def test_batch_accepts_independent_events(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    db_session,
) -> None:
    first = deepcopy(session_started_event)
    second = deepcopy(session_started_event)
    second["event_id"] = str(uuid4())
    second["session_id"] = str(uuid4())

    response = await client.post(
        "/api/v1/events/batch",
        json={"events": [first, second]},
        headers=ingest_headers,
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["status"] for item in results] == [
        "accepted",
        "accepted",
    ]
    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 2


async def test_batch_keeps_accepted_when_sibling_is_rejected(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    shopware_order_paid_event: dict,
    db_session,
) -> None:
    response = await client.post(
        "/api/v1/events/batch",
        json={
            "events": [
                session_started_event,
                shopware_order_paid_event,
            ]
        },
        headers=ingest_headers,
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["status"] == "accepted"
    assert results[1]["status"] == "rejected"
    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 1
