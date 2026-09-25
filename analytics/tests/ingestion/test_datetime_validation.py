from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from domains.ingestion.exceptions import EventValidationError
from domains.ingestion.validator import validate_http_event, validate_rabbit_event
from domains.projections.parsing import parse_datetime


def test_jsonschema_date_time_format_is_enabled() -> None:
    assert "date-time" in Draft202012Validator.FORMAT_CHECKER.checkers


def test_parse_datetime_rejects_yesterday() -> None:
    with pytest.raises(ValueError, match="RFC3339"):
        parse_datetime("yesterday")


def test_parse_datetime_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="RFC3339"):
        parse_datetime("2026-08-24T09:00:00")


def test_parse_datetime_accepts_rfc3339_z() -> None:
    parsed = parse_datetime("2026-08-24T09:00:00Z")
    assert parsed.tzinfo is not None


def test_http_schema_rejects_occurred_at_yesterday(
    session_started_event: dict,
) -> None:
    session_started_event["occurred_at"] = "yesterday"
    with pytest.raises(EventValidationError, match="occurred_at"):
        validate_http_event(session_started_event, origin="http://test")


def test_rabbit_schema_rejects_occurred_at_yesterday(
    shopware_order_paid_event: dict,
) -> None:
    event = deepcopy(shopware_order_paid_event)
    event["occurred_at"] = "yesterday"
    with pytest.raises(EventValidationError, match="occurred_at"):
        validate_rabbit_event(event)


async def test_http_invalid_occurred_at_returns_422(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
) -> None:
    session_started_event["occurred_at"] = "yesterday"
    response = await client.post(
        "/api/v1/events",
        json=session_started_event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert "occurred_at" in str(response.json()["detail"])
