import json
import logging

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractExchange, AbstractIncomingMessage
from sqlalchemy.exc import IntegrityError

from core.config import settings
from core.db.postgres import async_session_maker
from domains.ingestion.exceptions import EventIdCollisionError, EventValidationError
from domains.ingestion.service import persist_validated_event
from domains.ingestion.validator import validate_rabbit_event
from domains.projections.exceptions import ProjectionInvariantError

log = logging.getLogger(__name__)

# header Rabbit-сообщения, в котором consumer считает, сколько раз уже ретраили это сообщение
RETRY_ATTEMPT_HEADER = "x-retry-attempt"


def parse_rabbit_message_body(raw: bytes) -> dict:
    try:
        body = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EventValidationError(detail="Event must be valid JSON") from exc
    return validate_rabbit_event(body)


def _retry_attempt(message: AbstractIncomingMessage) -> int:
    # пустой словарь, чтобы не упасть на get
    headers = message.headers or {}
    # если нет заголовка, то это первая попытка обработать сообщение
    raw = headers.get(RETRY_ATTEMPT_HEADER, 0)
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError:
            return 0
    return 0


async def retry_or_dead_letter(
    message: AbstractIncomingMessage,
    retry_exchange: AbstractExchange | None,
) -> None:
    attempt = _retry_attempt(message)
    if retry_exchange is None or attempt >= settings.rabbitmq.max_retry_attempts:
        await message.reject(requeue=False)
        return

    headers = dict(message.headers or {})
    headers[RETRY_ATTEMPT_HEADER] = attempt + 1
    await retry_exchange.publish(
        Message(
            message.body,
            headers=headers,
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type=message.content_type,
            correlation_id=message.correlation_id,
            message_id=message.message_id,
        ),
        routing_key=message.routing_key or "shopware.retry",
    )
    await message.ack()


def is_permanent_ingest_error(exc: BaseException) -> bool:
    return isinstance(
        exc,
        (
            EventValidationError,
            EventIdCollisionError,
            ProjectionInvariantError,
            IntegrityError,
        ),
    )


async def _reject_to_dlq(message: AbstractIncomingMessage, reason: str) -> None:
    log.warning("%s, sending to DLQ", reason)
    await message.reject(requeue=False)


async def handle_shopware_message(
    message: AbstractIncomingMessage,
    retry_exchange: AbstractExchange | None = None,
) -> None:
    try:
        validated = parse_rabbit_message_body(message.body)
    except EventValidationError:
        await _reject_to_dlq(message, "Poison shopware message")
        return

    try:
        async with async_session_maker() as session:
            async with session.begin():
                await persist_validated_event(session, validated)
    except EventValidationError:
        await _reject_to_dlq(message, "Poison shopware message")
        return
    except EventIdCollisionError:
        await _reject_to_dlq(message, "Shopware event_id collision")
        return
    except Exception as exc:
        if is_permanent_ingest_error(exc):
            log.warning(
                "Permanent shopware ingest failure, sending to DLQ",
                exc_info=exc,
            )
            await message.reject(requeue=False)
            return
        log.exception("Transient shopware ingest failure")
        await retry_or_dead_letter(message, retry_exchange)
        return

    await message.ack()
