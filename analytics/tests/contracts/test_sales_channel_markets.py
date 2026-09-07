import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver

from core.config import settings
from domains.ingestion.registry import (
    http_event_schema_path,
    rabbit_event_schema_path,
)

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"

CHANNEL_CASES = [
    pytest.param(channel.id, channel.market_code, id=channel.market_code)
    for channel in settings.sales_channels
]


def _validator(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resolver = RefResolver(
        base_uri=schema_path.resolve().as_uri(),
        referrer=schema,
    )
    return Draft202012Validator(
        schema,
        resolver=resolver,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def _load_example(relative: str) -> dict:
    path = CONTRACTS_DIR / relative
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("channel_id", "market_code"), CHANNEL_CASES)
def test_session_started_schema_accepts_configured_channel(
    channel_id: str,
    market_code: str,
) -> None:
    event = deepcopy(_load_example("http/examples/valid/session-started.json"))
    event["sales_channel_id"] = channel_id
    event["market_code"] = market_code
    errors = list(
        _validator(http_event_schema_path("session_started")).iter_errors(event)
    )
    assert errors == []


@pytest.mark.parametrize(("channel_id", "market_code"), CHANNEL_CASES)
def test_order_paid_schema_accepts_configured_channel(
    channel_id: str,
    market_code: str,
) -> None:
    event = deepcopy(_load_example("rabbitmq/examples/valid/order-paid.json"))
    event["sales_channel_id"] = channel_id
    event["market_code"] = market_code
    errors = list(_validator(rabbit_event_schema_path("order_paid")).iter_errors(event))
    assert errors == []


def test_unknown_market_code_is_rejected_by_schema() -> None:
    event = deepcopy(_load_example("http/examples/valid/session-started.json"))
    event["market_code"] = "xx"
    errors = list(
        _validator(http_event_schema_path("session_started")).iter_errors(event)
    )
    assert errors
