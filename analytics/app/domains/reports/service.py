from sqlalchemy.ext.asyncio import AsyncSession

from domains.reports.filters import ReportFilters
from domains.reports.queries.contact_channels import query_contact_channels
from domains.reports.queries.funnel import query_funnel
from domains.reports.queries.overview import query_overview
from domains.reports.queries.payment_methods import query_payment_methods
from domains.reports.queries.period_comparison import query_period_comparison
from domains.reports.queries.products import query_products
from domains.reports.queries.sources import query_sources
from domains.reports.schemas import (
    ContactChannelsResponse,
    FunnelResponse,
    OverviewResponse,
    PaymentMethodsResponse,
    PeriodComparisonResponse,
    ProductsResponse,
    SourcesResponse,
)


async def overview(
    session: AsyncSession,
    filters: ReportFilters,
) -> OverviewResponse:
    return await query_overview(session, filters)


async def funnel(
    session: AsyncSession,
    filters: ReportFilters,
) -> FunnelResponse:
    return await query_funnel(session, filters)


async def sources(
    session: AsyncSession,
    filters: ReportFilters,
) -> SourcesResponse:
    return await query_sources(session, filters)


async def contact_channels(
    session: AsyncSession,
    filters: ReportFilters,
) -> ContactChannelsResponse:
    return await query_contact_channels(session, filters)


async def products(
    session: AsyncSession,
    filters: ReportFilters,
) -> ProductsResponse:
    return await query_products(session, filters)


async def payment_methods(
    session: AsyncSession,
    filters: ReportFilters,
) -> PaymentMethodsResponse:
    return await query_payment_methods(session, filters)


async def period_comparison(
    session: AsyncSession,
    filters: ReportFilters,
) -> PeriodComparisonResponse:
    return await query_period_comparison(session, filters)
