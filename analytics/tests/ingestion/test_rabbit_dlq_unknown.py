import json
from typing import cast

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
