from core.config import settings
from domains.ingestion.rate_limit import reset_rate_limit_store
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
