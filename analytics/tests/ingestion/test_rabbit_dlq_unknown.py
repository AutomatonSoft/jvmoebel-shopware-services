import json
from copy import deepcopy
from typing import cast
from uuid import UUID

import pytest
from aio_pika.abc import AbstractExchange, AbstractIncomingMessage
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError

from domains.ingestion.consumer import (
    handle_shopware_message,
    is_permanent_ingest_error,
)
from domains.ingestion.exceptions import EventValidationError
from domains.ingestion.validator import validate_rabbit_event
from domains.projections.exceptions import ProjectionInvariantError
from domains.projections.models.facts import Refund
from domains.projections.models.journal import Event


class FakeIncomingMessage:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.headers: dict | None = {}
        self.routing_key = "shopware.order.paid"
        self.content_type = "application/json"
        self.correlation_id = None
        self.message_id = None
        self.acked = False
        self.rejected = False
        self.requeue: bool | None = None

    async def ack(self) -> None:
        self.acked = True

    async def reject(self, requeue: bool = False) -> None:
        self.rejected = True
        self.requeue = requeue


class FakeRetryExchange:
    def __init__(self) -> None:
        self.published: list[dict] = []

    async def publish(self, message, routing_key: str = "") -> None:
        self.published.append({"message": message, "routing_key": routing_key})


async def test_unknown_event_type_goes_to_dlq_without_retry(
    shopware_order_paid_event: dict,
    db_session,
) -> None:
    shopware_order_paid_event["event_type"] = "not_a_real_event"
    message = FakeIncomingMessage(
        body=json.dumps(shopware_order_paid_event).encode("utf-8"),
    )
    # считай что у класс message не фейковый, а AbstractIncomingMessage. Нужно для типизации
    await handle_shopware_message(cast(AbstractIncomingMessage, message))

    assert message.rejected is True
    assert message.requeue is False
    assert message.acked is False

    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 0


async def test_valid_shopware_event_is_not_poison(
    shopware_order_paid_event: dict,
) -> None:
    validated = validate_rabbit_event(shopware_order_paid_event)
    assert validated["event_type"] == "order_paid"


async def test_frontend_type_on_rabbit_is_poison(
    session_started_event: dict,
) -> None:
    with pytest.raises(EventValidationError, match="not allowed"):
        validate_rabbit_event(session_started_event)


async def test_rabbit_replay_acks_duplicate(
    shopware_order_paid_event: dict,
    db_session,
) -> None:
    body = json.dumps(shopware_order_paid_event).encode("utf-8")
    first = FakeIncomingMessage(body)
    second = FakeIncomingMessage(body)

    await handle_shopware_message(cast(AbstractIncomingMessage, first))
    await handle_shopware_message(cast(AbstractIncomingMessage, second))

    assert first.acked is True
    assert second.acked is True
    assert second.rejected is False
    count = await db_session.scalar(select(func.count()).select_from(Event))
    assert count == 1


async def test_rabbit_payload_collision_goes_to_dlq(
    shopware_order_paid_event: dict,
    db_session,
) -> None:
    first = FakeIncomingMessage(
        json.dumps(shopware_order_paid_event).encode("utf-8"),
    )
    colliding = deepcopy(shopware_order_paid_event)
    colliding["payload"] = {
        **colliding["payload"],
        "total_amount": "1.00",
    }
    second = FakeIncomingMessage(json.dumps(colliding).encode("utf-8"))

    await handle_shopware_message(cast(AbstractIncomingMessage, first))
    await handle_shopware_message(cast(AbstractIncomingMessage, second))

    assert first.acked is True
    assert second.rejected is True
    assert second.requeue is False
    assert second.acked is False

    stored = await db_session.get(Event, UUID(shopware_order_paid_event["event_id"]))
    assert stored is not None
    assert stored.body["payload"]["total_amount"] == "2499.00"


async def test_rabbit_event_type_collision_goes_to_dlq(
    shopware_order_paid_event: dict,
    load_shopware_event,
    db_session,
) -> None:
    first = FakeIncomingMessage(
        json.dumps(shopware_order_paid_event).encode("utf-8"),
    )
    colliding = load_shopware_event("order-created")
    colliding["event_id"] = shopware_order_paid_event["event_id"]
    second = FakeIncomingMessage(json.dumps(colliding).encode("utf-8"))

    await handle_shopware_message(cast(AbstractIncomingMessage, first))
    await handle_shopware_message(cast(AbstractIncomingMessage, second))

    assert second.rejected is True
    assert second.requeue is False
    assert second.acked is False
    stored = await db_session.get(Event, UUID(shopware_order_paid_event["event_id"]))
    assert stored is not None
    assert stored.event_type == "order_paid"


async def test_rabbit_aggregate_collision_goes_to_dlq(
    shopware_order_paid_event: dict,
    db_session,
) -> None:
    first = FakeIncomingMessage(
        json.dumps(shopware_order_paid_event).encode("utf-8"),
    )
    colliding = deepcopy(shopware_order_paid_event)
    colliding["order_id"] = "018f3333333333333333333333333999"
    colliding["aggregate_id"] = "018f3333333333333333333333333999"
    second = FakeIncomingMessage(json.dumps(colliding).encode("utf-8"))

    await handle_shopware_message(cast(AbstractIncomingMessage, first))
    await handle_shopware_message(cast(AbstractIncomingMessage, second))

    assert second.rejected is True
    assert second.requeue is False
    assert second.acked is False
    stored = await db_session.get(Event, UUID(shopware_order_paid_event["event_id"]))
    assert stored is not None
    assert stored.order_id == shopware_order_paid_event["order_id"]
    assert stored.aggregate_id == shopware_order_paid_event["aggregate_id"]


def test_permanent_ingest_errors_are_classified() -> None:
    assert is_permanent_ingest_error(
        IntegrityError("INSERT", {}, Exception("unique")),
    )
    assert is_permanent_ingest_error(ProjectionInvariantError("missing id"))
    assert is_permanent_ingest_error(EventValidationError())
    assert not is_permanent_ingest_error(
        OperationalError("SELECT", {}, Exception("connection refused")),
    )
    assert not is_permanent_ingest_error(RuntimeError("timeout"))


async def test_duplicate_refund_id_goes_to_dlq_without_retry(
    load_shopware_event,
    db_session,
) -> None:
    first_body = load_shopware_event("refund-created")
    second_body = load_shopware_event("refund-created")
    retry = FakeRetryExchange()

    first = FakeIncomingMessage(json.dumps(first_body).encode("utf-8"))
    second = FakeIncomingMessage(json.dumps(second_body).encode("utf-8"))
    await handle_shopware_message(
        cast(AbstractIncomingMessage, first),
        cast(AbstractExchange, retry),
    )
    await handle_shopware_message(
        cast(AbstractIncomingMessage, second),
        cast(AbstractExchange, retry),
    )

    assert first.acked is True
    assert second.rejected is True
    assert second.requeue is False
    assert second.acked is False
    assert retry.published == []
    stored = await db_session.get(Refund, first_body["refund_id"])
    assert stored is not None
    assert str(stored.event_id) == first_body["event_id"]


async def test_projection_invariant_goes_to_dlq_without_retry(
    shopware_order_paid_event: dict,
    monkeypatch,
) -> None:
    async def boom(*args, **kwargs):
        raise ProjectionInvariantError("order_paid missing required order_id")

    monkeypatch.setattr(
        "domains.ingestion.consumer.persist_validated_event",
        boom,
    )
    retry = FakeRetryExchange()
    message = FakeIncomingMessage(
        json.dumps(shopware_order_paid_event).encode("utf-8"),
    )
    await handle_shopware_message(
        cast(AbstractIncomingMessage, message),
        cast(AbstractExchange, retry),
    )

    assert message.rejected is True
    assert message.requeue is False
    assert message.acked is False
    assert retry.published == []


async def test_mismatched_refund_after_order_goes_to_dlq(
    load_shopware_event,
    db_session,
) -> None:
    paid = load_shopware_event("order-paid")
    refund = load_shopware_event("refund-created")
    refund["order_id"] = paid["order_id"]
    refund["payload"]["currency"] = "USD"
    retry = FakeRetryExchange()
    first = FakeIncomingMessage(json.dumps(paid).encode("utf-8"))
    second = FakeIncomingMessage(json.dumps(refund).encode("utf-8"))

    await handle_shopware_message(
        cast(AbstractIncomingMessage, first),
        cast(AbstractExchange, retry),
    )
    await handle_shopware_message(
        cast(AbstractIncomingMessage, second),
        cast(AbstractExchange, retry),
    )

    assert first.acked is True
    assert second.rejected is True
    assert second.requeue is False
    assert second.acked is False
    assert retry.published == []
    stored = await db_session.get(Refund, refund["refund_id"])
    assert stored is None


async def test_operational_error_retries(
    shopware_order_paid_event: dict,
    monkeypatch,
) -> None:
    async def boom(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(
        "domains.ingestion.consumer.persist_validated_event",
        boom,
    )
    retry = FakeRetryExchange()
    message = FakeIncomingMessage(
        json.dumps(shopware_order_paid_event).encode("utf-8"),
    )
    await handle_shopware_message(
        cast(AbstractIncomingMessage, message),
        cast(AbstractExchange, retry),
    )

    assert message.acked is True
    assert message.rejected is False
    assert len(retry.published) == 1
    assert retry.published[0]["routing_key"] == "shopware.order.paid"
