import json
from copy import deepcopy
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from domains.ingestion.exceptions import EventIdCollisionError
from domains.projections.models.journal import Event

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def _product_viewed_event() -> dict:
    path = CONTRACTS / "http" / "examples" / "valid" / "product-viewed.json"
    return json.loads(path.read_text(encoding="utf-8"))


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


async def test_same_event_id_different_payload_is_conflict(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    db_session,
) -> None:
    colliding = deepcopy(session_started_event)
    colliding["payload"] = {
        **colliding["payload"],
        "landing_page": "https://www.jvmoebel.de/chairs/chair-001",
    }

    first = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    second = await client.post(
        "/api/v1/events",
        json=colliding,
        headers=ingest_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json() == {
        "detail": "event_id collision: payload does not match stored event",
    }

    stored = await db_session.get(Event, UUID(session_started_event["event_id"]))
    assert stored is not None
    assert stored.body["payload"]["landing_page"] == (
        session_started_event["payload"]["landing_page"]
    )
    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 1


async def test_same_event_id_different_event_type_is_conflict(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    db_session,
) -> None:
    colliding = _product_viewed_event()
    colliding["event_id"] = session_started_event["event_id"]

    first = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    second = await client.post(
        "/api/v1/events",
        json=colliding,
        headers=ingest_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    stored = await db_session.get(Event, UUID(session_started_event["event_id"]))
    assert stored is not None
    assert stored.event_type == "session_started"


async def test_persist_collision_raises(
    persist_event,
    session_started_event: dict,
) -> None:
    colliding = deepcopy(session_started_event)
    colliding["payload"] = {
        **colliding["payload"],
        "landing_page": "https://www.jvmoebel.de/chairs/chair-001",
    }
    assert await persist_event(session_started_event) == "accepted"
    with pytest.raises(EventIdCollisionError):
        await persist_event(colliding)


async def test_batch_collision_returns_409(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    db_session,
) -> None:
    colliding = deepcopy(session_started_event)
    colliding["payload"] = {
        **colliding["payload"],
        "landing_page": "https://www.jvmoebel.de/chairs/chair-001",
    }

    response = await client.post(
        "/api/v1/events/batch",
        json={"events": [session_started_event, colliding]},
        headers=ingest_headers,
    )
    assert response.status_code == 409
    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 1
