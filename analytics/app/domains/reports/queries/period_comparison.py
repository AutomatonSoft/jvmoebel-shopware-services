from sqlalchemy.ext.asyncio import AsyncSession

from domains.reports.filters import ReportFilters, previous_period
from domains.reports.queries.overview import query_overview
from domains.reports.schemas import PeriodComparisonResponse


async def query_period_comparison(
    session: AsyncSession,
    filters: ReportFilters,
) -> PeriodComparisonResponse:
    return PeriodComparisonResponse(
        current=await query_overview(session, filters),
        previous=await query_overview(session, previous_period(filters)),
    )
