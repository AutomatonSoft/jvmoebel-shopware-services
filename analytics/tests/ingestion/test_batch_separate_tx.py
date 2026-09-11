from collections.abc import AsyncIterator
from copy import deepcopy
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError, ProgrammingError

from domains.ingestion import batch as batch_module
from domains.ingestion.service import ingest_http_event as real_ingest_http_event
from domains.projections.models.journal import Event
from main import app_without_middleware as app


@pytest.fixture
async def silent_500_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
    # фикстура client подменяет get_async_session на тестовую БД. ServerErrorMiddleware после отправки 500
    # снова бросает Exception; оставляем HTTP-ответ, чтобы проверить статус.
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as silent_client:
        yield silent_client


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


def _two_session_events(session_started_event: dict) -> tuple[dict, dict]:
    first = deepcopy(session_started_event)
    second = deepcopy(session_started_event)
    second["event_id"] = str(uuid4())
    second["session_id"] = str(uuid4())
    return first, second


async def test_batch_projection_error_returns_500(
    silent_500_client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    db_session,
    monkeypatch,
) -> None:
    first, second = _two_session_events(session_started_event)
    calls = {"n": 0}

    async def fail_on_second(
        session: Any,
        item: object,
        *,
        origin: str | None,
    ) -> Any:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("projection failed")
        return await real_ingest_http_event(session, item, origin=origin)

    monkeypatch.setattr(batch_module, "ingest_http_event", fail_on_second)

    response = await silent_500_client.post(
        "/api/v1/events/batch",
        json={"events": [first, second]},
        headers=ingest_headers,
    )
    assert response.status_code == 500
    assert response.json() == {"message": "An unexpected error has occurred."}
    assert "results" not in response.json()
    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 1


async def test_batch_postgres_unavailable_returns_500(
    silent_500_client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    monkeypatch,
) -> None:
    async def fail_postgres(
        session: Any,
        item: object,
        *,
        origin: str | None,
    ) -> Any:
        raise OperationalError(
            "INSERT INTO events",
            {},
            Exception("could not connect to server"),
        )

    monkeypatch.setattr(batch_module, "ingest_http_event", fail_postgres)

    response = await silent_500_client.post(
        "/api/v1/events/batch",
        json={"events": [session_started_event]},
        headers=ingest_headers,
    )
    assert response.status_code == 500
    assert response.json() == {"message": "An unexpected error has occurred."}


async def test_batch_missing_schema_returns_503(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    monkeypatch,
) -> None:
    async def fail_schema(
        session: Any,
        item: object,
        *,
        origin: str | None,
    ) -> Any:
        raise ProgrammingError(
            "SELECT 1",
            {},
            Exception("UndefinedTableError: relation events does not exist"),
        )

    monkeypatch.setattr(batch_module, "ingest_http_event", fail_schema)

    response = await client.post(
        "/api/v1/events/batch",
        json={"events": [session_started_event]},
        headers=ingest_headers,
    )
    assert response.status_code == 503
    assert response.json() == {
        "message": "Database schema is not ready. Apply Alembic migrations."
    }
