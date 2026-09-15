from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import Touch, copy_attribution_known_at
from domains.projections.models.entities import Lead, ManualSale, Order, Visitor


def _order_as_of(order: Order) -> datetime | None:
    if order.paid_event_id is not None:
        return order.paid_at
    return order.created_at


async def refresh_dependent_snapshots(
    session: AsyncSession,
    visitor: Visitor,
    touch_at: datetime,
    touch: Touch,
) -> None:
    leads = await session.scalars(
        select(Lead).where(
            Lead.visitor_id == visitor.visitor_id,
            Lead.created_at.is_not(None),
            Lead.created_at >= touch_at,
        )
    )
    for lead in leads:
        if lead.created_at is None:
            continue
        copy_attribution_known_at(
            visitor,
            lead,
            as_of=lead.created_at,
            incoming=touch,
        )

    orders = await session.scalars(
        select(Order).where(
            Order.visitor_id == visitor.visitor_id,
            or_(
                Order.created_at >= touch_at,
                Order.paid_at >= touch_at,
            ),
        )
    )
    for order in orders:
        as_of = _order_as_of(order)
        if as_of is None:
            continue
        copy_attribution_known_at(
            visitor,
            order,
            as_of=as_of,
            incoming=touch,
        )

    sales = await session.scalars(
        select(ManualSale).where(
            ManualSale.visitor_id == visitor.visitor_id,
            ManualSale.confirmed_at.is_not(None),
            ManualSale.confirmed_at >= touch_at,
        )
    )
    for sale in sales:
        if sale.confirmed_at is None:
            continue
        copy_attribution_known_at(
            visitor,
            sale,
            as_of=sale.confirmed_at,
            incoming=touch,
        )
