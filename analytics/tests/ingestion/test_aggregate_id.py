from copy import deepcopy

import pytest

from domains.ingestion.exceptions import EventValidationError
from domains.ingestion.validator import validate_rabbit_event


def test_rabbit_accepts_matching_aggregate_id(
    shopware_order_paid_event: dict,
) -> None:
    validated = validate_rabbit_event(shopware_order_paid_event)
    assert validated["aggregate_id"] == validated["order_id"]


def test_rabbit_rejects_mismatched_order_aggregate_id(
    shopware_order_paid_event: dict,
) -> None:
    event = deepcopy(shopware_order_paid_event)
    event["aggregate_id"] = "018f3333333333333333333333333399"
    with pytest.raises(EventValidationError, match="aggregate_id must equal order_id"):
        validate_rabbit_event(event)


def test_rabbit_rejects_mismatched_lead_aggregate_id(
    load_shopware_event,
) -> None:
    event = load_shopware_event("lead-created")
    event["aggregate_id"] = "018f1111111111111111111111111199"
    with pytest.raises(EventValidationError, match="aggregate_id must equal lead_id"):
        validate_rabbit_event(event)
