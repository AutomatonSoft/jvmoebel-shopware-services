from sqlalchemy.ext.asyncio import AsyncSession

from domains.reports.filters import ReportFilters
from domains.reports.metrics import (
    count_leads,
    count_orders_created,
    count_orders_paid,
    count_sessions,
    count_visitors,
)
from domains.reports.money_agg import aggregate_money
from domains.reports.schemas import OverviewResponse


async def query_overview(
    session: AsyncSession,
    filters: ReportFilters,
) -> OverviewResponse:
    return OverviewResponse(
        visitors=await count_visitors(session, filters),
        sessions=await count_sessions(session, filters),
        leads=await count_leads(session, filters),
        orders_created=await count_orders_created(session, filters),
        orders_paid=await count_orders_paid(session, filters),
        money=await aggregate_money(session, filters),
    )
