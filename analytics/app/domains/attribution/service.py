from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import copy_attribution_snapshot
from domains.projections.models.entities import Order, Visitor


async def refresh_dependent_snapshots(
    session: AsyncSession,
    visitor: Visitor,
    touch_at: datetime,
) -> None:
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
        if order.paid_event_id is not None:
            continue
        copy_attribution_snapshot(visitor, order)
