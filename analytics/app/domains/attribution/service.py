from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.rules import copy_attribution_snapshot
from domains.projections.models.entities import Lead, ManualSale, Order, Visitor


async def refresh_dependent_snapshots(
    session: AsyncSession,
    visitor: Visitor,
    touch_at: datetime,
) -> None:
    leads = await session.scalars(
        select(Lead).where(
            Lead.visitor_id == visitor.visitor_id,
            Lead.created_at.is_not(None),
            Lead.created_at >= touch_at,
        )
    )
    for lead in leads:
        copy_attribution_snapshot(visitor, lead)

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
        copy_attribution_snapshot(visitor, order)

    sales = await session.scalars(
        select(ManualSale).where(
            ManualSale.visitor_id == visitor.visitor_id,
            ManualSale.confirmed_at.is_not(None),
            ManualSale.confirmed_at >= touch_at,
        )
    )
    for sale in sales:
        copy_attribution_snapshot(visitor, sale)
