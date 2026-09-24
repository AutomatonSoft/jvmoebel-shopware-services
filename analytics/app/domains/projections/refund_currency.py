import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.projections.exceptions import ProjectionInvariantError
from domains.projections.models.entities import Order
from domains.projections.models.facts import Refund
from domains.projections.models.journal import Event

CURRENCY_MISMATCH = "currency_mismatch"

log = logging.getLogger(__name__)


async def _set_event_invalid_reason(
    session: AsyncSession,
    event_id: uuid.UUID,
    reason: str | None,
) -> None:
    event = await session.get(Event, event_id)
    if event is None:
        return
    body = dict(event.body)
    payload = dict(body.get("payload") or {})
    if reason is None:
        payload.pop("invalid_reason", None)
    else:
        payload["invalid_reason"] = reason
    body["payload"] = payload
    event.body = body


def require_matching_order_currency(
    order: Order | None,
    *,
    refund_id: str,
    refund_currency: str,
) -> None:
    if order is None or order.currency is None or order.currency == refund_currency:
        return
    raise ProjectionInvariantError(
        f"refund_created {refund_id} currency {refund_currency} "
        f"does not match order {order.order_id} currency {order.currency}"
    )


async def sync_refund_currency_validity(
    session: AsyncSession,
    order: Order,
) -> None:
    if order.currency is None:
        return
    refunds = await session.scalars(
        select(Refund).where(Refund.order_id == order.order_id)
    )
    for refund in refunds:
        if refund.currency != order.currency:
            if refund.invalid_reason != CURRENCY_MISMATCH:
                log.warning(
                    "refund_created %s currency %s does not match order %s currency %s",
                    refund.refund_id,
                    refund.currency,
                    order.order_id,
                    order.currency,
                )
                refund.invalid_reason = CURRENCY_MISMATCH
                await _set_event_invalid_reason(
                    session,
                    refund.event_id,
                    CURRENCY_MISMATCH,
                )
        elif refund.invalid_reason is not None:
            refund.invalid_reason = None
            await _set_event_invalid_reason(session, refund.event_id, None)
