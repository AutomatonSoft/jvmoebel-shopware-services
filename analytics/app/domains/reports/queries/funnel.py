from sqlalchemy.ext.asyncio import AsyncSession

from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    count_cart_adders,
    count_checkout_visitors,
    count_leads,
    count_orders_created,
    count_orders_paid,
    count_product_viewers,
    count_sessions,
    count_visitors,
)
from domains.reports.schemas import FunnelResponse


async def query_funnel(
    session: AsyncSession,
    filters: ReportFilters,
) -> FunnelResponse:
    return FunnelResponse(
        visitors=await count_visitors(session, filters),
        sessions=await count_sessions(session, filters),
        product_viewers=await count_product_viewers(session, filters),
        cart_adders=await count_cart_adders(session, filters),
        checkouts=await count_checkout_visitors(session, filters),
        leads=await count_leads(session, filters),
        orders_created=await count_orders_created(session, filters),
        orders_paid=await count_orders_paid(session, filters),
    )
