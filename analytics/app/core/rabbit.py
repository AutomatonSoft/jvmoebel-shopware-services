import asyncio
import logging
from dataclasses import dataclass

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractQueue,
)

from core.config import settings
from domains.ingestion.consumer import handle_shopware_message

log = logging.getLogger(__name__)

EVENTS_EXCHANGE = "shopware.analytics.events"
RETRY_EXCHANGE = "shopware.analytics.retry"
DLX_EXCHANGE = "shopware.analytics.dlx"
RETRY_QUEUE = "analytics.shopware.events.retry"
DLQ_QUEUE = "analytics.shopware.events.dlq"

ROUTING_KEYS = (
    "shopware.lead.created",
    "shopware.contact.received",
    "shopware.lead.status_changed",
    "shopware.customer.linked",
    "shopware.order.created",
    "shopware.order.updated",
    "shopware.order.paid",
    "shopware.order.cancelled",
    "shopware.manual_sale.created",
    "shopware.manual_sale.updated",
    "shopware.manual_sale.cancelled",
    "shopware.refund.created",
)


@dataclass(frozen=True)
class ShopwareTopology:
    events_exchange: AbstractExchange
    retry_exchange: AbstractExchange
    events_queue: AbstractQueue


async def declare_topology(channel: AbstractChannel) -> ShopwareTopology:
    events_exchange = await channel.declare_exchange(
        EVENTS_EXCHANGE,
        ExchangeType.TOPIC,
        durable=True,
    )
    retry_exchange = await channel.declare_exchange(
        RETRY_EXCHANGE,
        ExchangeType.TOPIC,
        durable=True,
    )
    dlx_exchange = await channel.declare_exchange(
        DLX_EXCHANGE,
        ExchangeType.TOPIC,
        durable=True,
    )

    events_queue = await channel.declare_queue(
        settings.rabbitmq.events_queue,
        durable=True,
        arguments={"x-dead-letter-exchange": DLX_EXCHANGE},
    )
    for routing_key in ROUTING_KEYS:
        await events_queue.bind(events_exchange, routing_key=routing_key)

    retry_queue = await channel.declare_queue(
        RETRY_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": settings.rabbitmq.retry_ttl_ms,
            "x-dead-letter-exchange": EVENTS_EXCHANGE,
        },
    )
    await retry_queue.bind(retry_exchange, routing_key="shopware.#")

    dlq = await channel.declare_queue(DLQ_QUEUE, durable=True)
    await dlq.bind(dlx_exchange, routing_key="#")

    return ShopwareTopology(
        events_exchange=events_exchange,
        retry_exchange=retry_exchange,
        events_queue=events_queue,
    )


async def consume_shopware_events() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq.url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=settings.rabbitmq.prefetch)
        topology = await declare_topology(channel)

        async def on_message(message: AbstractIncomingMessage) -> None:
            await handle_shopware_message(message, topology.retry_exchange)

        await topology.events_queue.consume(on_message)
        log.info(
            "Consuming %s",
            settings.rabbitmq.events_queue,
        )
        await asyncio.Future()
