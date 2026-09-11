import time

from core.config import settings
from domains.ingestion.rate_limit import (
    _consume,
    rate_limit_store_keys,
    rate_limit_store_size,
    reset_rate_limit_store,
)
from tests.reports.helpers import report_params, uniquify_ids

OTHER_ORIGIN = "https://www.jvmoebel.de"


async def test_ingest_exceeding_limit_returns_429(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    monkeypatch,
) -> None:
    reset_rate_limit_store()
    monkeypatch.setattr(settings, "ingest_rate_limit", 2)

    first = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers=ingest_headers,
    )
    second = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers=ingest_headers,
    )
    third = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers=ingest_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "Rate limit exceeded"
    assert third.headers["Retry-After"].isdigit()


async def test_ingest_rate_limit_is_per_origin(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    monkeypatch,
) -> None:
    reset_rate_limit_store()
    monkeypatch.setattr(settings, "ingest_rate_limit", 1)

    first = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers=ingest_headers,
    )
    other = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers={**ingest_headers, "Origin": OTHER_ORIGIN},
    )
    blocked = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers=ingest_headers,
    )

    assert first.status_code == 200
    assert other.status_code == 200
    assert blocked.status_code == 429


async def test_reports_are_not_rate_limited(
    client,
    ingest_headers: dict[str, str],
    read_auth_headers: dict[str, str],
    session_started_event: dict,
    monkeypatch,
) -> None:
    reset_rate_limit_store()
    monkeypatch.setattr(settings, "ingest_rate_limit", 1)

    ingest = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers=ingest_headers,
    )
    overview = await client.get(
        "/api/v1/analytics/overview",
        params=report_params(),
        headers=read_auth_headers,
    )
    blocked = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers=ingest_headers,
    )

    assert ingest.status_code == 200
    assert overview.status_code == 200
    assert blocked.status_code == 429


async def test_unauthenticated_ingest_does_not_fill_store(
    client,
    session_started_event: dict,
) -> None:
    reset_rate_limit_store()

    response = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 401
    assert rate_limit_store_size() == 0


async def test_invalid_token_does_not_fill_store(
    client,
    invalid_auth_headers: dict[str, str],
    session_started_event: dict,
) -> None:
    reset_rate_limit_store()

    response = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers={**invalid_auth_headers, "Origin": "https://evil.example"},
    )

    assert response.status_code == 401
    assert rate_limit_store_size() == 0


async def test_unknown_origins_share_ip_bucket(
    client,
    ingest_auth_headers: dict[str, str],
    session_started_event: dict,
    monkeypatch,
) -> None:
    reset_rate_limit_store()
    monkeypatch.setattr(settings, "ingest_rate_limit", 1)

    first = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers={**ingest_auth_headers, "Origin": "https://evil-1.example"},
    )
    second = await client.post(
        "/api/v1/events",
        json=uniquify_ids(session_started_event),
        headers={**ingest_auth_headers, "Origin": "https://evil-2.example"},
    )

    assert first.status_code == 422
    assert second.status_code == 429
    assert rate_limit_store_size() == 1
    assert next(iter(rate_limit_store_keys())).startswith("ip:")


def test_expired_keys_are_evicted(monkeypatch) -> None:
    reset_rate_limit_store()
    start = 1_700_000_000.0
    monkeypatch.setattr(time, "time", lambda: start)

    assert _consume("origin:a", limit=10, window_seconds=60, max_keys=1024) is None
    assert rate_limit_store_keys() == frozenset({"origin:a"})

    monkeypatch.setattr(time, "time", lambda: start + 61)
    assert _consume("origin:b", limit=10, window_seconds=60, max_keys=1024) is None
    assert rate_limit_store_keys() == frozenset({"origin:b"})


def test_store_rejects_new_key_when_full(monkeypatch) -> None:
    reset_rate_limit_store()
    start = 1_700_000_000.0
    monkeypatch.setattr(time, "time", lambda: start)

    assert _consume("origin:a", limit=10, window_seconds=60, max_keys=2) is None
    assert _consume("origin:b", limit=10, window_seconds=60, max_keys=2) is None
    retry_after = _consume("origin:c", limit=10, window_seconds=60, max_keys=2)

    assert retry_after is not None
    assert retry_after >= 1
    assert rate_limit_store_keys() == frozenset({"origin:a", "origin:b"})
    assert _consume("origin:a", limit=10, window_seconds=60, max_keys=2) is None
