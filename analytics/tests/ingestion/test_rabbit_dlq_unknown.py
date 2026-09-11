import json
from copy import deepcopy
from typing import cast
from uuid import UUID

import pytest
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import func, select

from domains.ingestion.consumer import handle_shopware_message
from domains.ingestion.exceptions import EventValidationError
from domains.ingestion.validator import validate_rabbit_event
from domains.projections.models.journal import Event


class FakeIncomingMessage:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.headers: dict | None = {}
        self.routing_key = "shopware.order.paid"
        self.acked = False
        self.rejected = False
        self.requeue: bool | None = None

    async def ack(self) -> None:
        self.acked = True

    async def reject(self, requeue: bool = False) -> None:
        self.rejected = True
        self.requeue = requeue


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
