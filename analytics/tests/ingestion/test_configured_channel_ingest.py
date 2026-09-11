import json
from copy import deepcopy
from urllib.parse import urlsplit

import pytest

from core.config import settings
from domains.ingestion.exceptions import EventValidationError
from domains.ingestion.registry import HTTP_CONTRACTS_ROOT
from domains.ingestion.validator import validate_rabbit_event

CHANNEL_CASES = [
    pytest.param(channel.id, channel.market_code, id=channel.market_code)
    for channel in settings.sales_channels
]


def _contract_markets() -> set[str]:
    schema = json.loads(
        (HTTP_CONTRACTS_ROOT / "schemas" / "common" / "market-code.schema.json").read_text(
            encoding="utf-8",
        )
    )
    return set(schema["enum"])


def test_test_env_lists_all_contract_markets() -> None:
    codes = {channel.market_code for channel in settings.sales_channels}
    assert codes == _contract_markets()


def _channel_event_domain(channel_id: str) -> str:
    channel = next(
        item for item in settings.sales_channels if item.id == channel_id
    )
    origin = next(
        item for item in channel.origins if item != "http://test"
    )
    host = urlsplit(origin).hostname
    assert host is not None
    return host


@pytest.mark.parametrize(("channel_id", "market_code"), CHANNEL_CASES)
async def test_http_accepts_configured_channel(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    channel_id: str,
    market_code: str,
) -> None:
    event = deepcopy(session_started_event)
    event["sales_channel_id"] = channel_id
    event["market_code"] = market_code
    event["domain"] = _channel_event_domain(channel_id)
    response = await client.post(
        "/api/v1/events",
        json=event,
        headers=ingest_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


@pytest.mark.parametrize(("channel_id", "market_code"), CHANNEL_CASES)
async def test_http_rejects_foreign_origin_for_channel(
    client,
    ingest_auth_headers: dict[str, str],
    session_started_event: dict,
    channel_id: str,
    market_code: str,
) -> None:
    other = next(
        (channel for channel in settings.sales_channels if channel.id != channel_id),
        None,
    )
    if other is None:
        pytest.skip("Need at least two configured sales channels")
    foreign_origin = next(
        origin for origin in other.origins if origin != "http://test"
    )
    event = deepcopy(session_started_event)
    event["sales_channel_id"] = channel_id
    event["market_code"] = market_code
    event["domain"] = _channel_event_domain(channel_id)
    response = await client.post(
        "/api/v1/events",
        json=event,
        headers={**ingest_auth_headers, "Origin": foreign_origin},
    )
    assert response.status_code == 422
    assert "Origin" in response.json()["detail"]


@pytest.mark.parametrize(("channel_id", "market_code"), CHANNEL_CASES)
async def test_http_rejects_foreign_domain_for_channel(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    channel_id: str,
    market_code: str,
) -> None:
    other = next(
        (channel for channel in settings.sales_channels if channel.id != channel_id),
        None,
    )
    if other is None:
        pytest.skip("Need at least two configured sales channels")
    event = deepcopy(session_started_event)
    event["sales_channel_id"] = channel_id
    event["market_code"] = market_code
    event["domain"] = _channel_event_domain(other.id)
    response = await client.post(
        "/api/v1/events",
        json=event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert "domain" in response.json()["detail"]


@pytest.mark.parametrize(("channel_id", "market_code"), CHANNEL_CASES)
async def test_http_rejects_foreign_market_code_for_channel(
    client,
    ingest_headers: dict[str, str],
    session_started_event: dict,
    channel_id: str,
    market_code: str,
) -> None:
    other_market = next(
        (
            channel.market_code
            for channel in settings.sales_channels
            if channel.market_code != market_code
        ),
        None,
    )
    if other_market is None:
        pytest.skip("Need at least two configured sales channels")
    event = deepcopy(session_started_event)
    event["sales_channel_id"] = channel_id
    event["market_code"] = other_market
    response = await client.post(
        "/api/v1/events",
        json=event,
        headers=ingest_headers,
    )
    assert response.status_code == 422
    assert "market_code" in response.json()["detail"]


@pytest.mark.parametrize(("channel_id", "market_code"), CHANNEL_CASES)
def test_rabbit_accepts_configured_channel(
    shopware_order_paid_event: dict,
    channel_id: str,
    market_code: str,
) -> None:
    event = deepcopy(shopware_order_paid_event)
    event["sales_channel_id"] = channel_id
    event["market_code"] = market_code
    validated = validate_rabbit_event(event)
    assert validated["sales_channel_id"] == channel_id
    assert validated["market_code"] == market_code


def test_rabbit_rejects_unknown_sales_channel(
    shopware_order_paid_event: dict,
) -> None:
    event = deepcopy(shopware_order_paid_event)
    event["sales_channel_id"] = "f" * 32
    with pytest.raises(EventValidationError, match="Unknown sales_channel_id"):
        validate_rabbit_event(event)
