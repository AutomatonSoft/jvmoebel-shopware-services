from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import get_async_session
from domains.base.dependencies import require_read_access
from domains.reports import service
from domains.reports.dependencies import (
    parse_period_comparison_filters,
    parse_report_filters,
)
from domains.reports.filters import PeriodComparisonQuery, ReportFilters
from domains.reports.schemas import (
    ContactChannelsResponse,
    FunnelResponse,
    OverviewResponse,
    PaymentMethodsResponse,
    PeriodComparisonResponse,
    ProductsResponse,
    SourcesResponse,
)

router = APIRouter(
    prefix="/analytics",
    tags=["Reports"],
    dependencies=[Depends(require_read_access)],
)

Filters = Annotated[ReportFilters, Depends(parse_report_filters)]
ComparisonQuery = Annotated[
    PeriodComparisonQuery,
    Depends(parse_period_comparison_filters),
]
DbSession = Annotated[AsyncSession, Depends(get_async_session)]


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    filters: Filters,
    session: DbSession,
) -> OverviewResponse:
    return await service.overview(session, filters)


@router.get("/funnel", response_model=FunnelResponse)
async def get_funnel(
    filters: Filters,
    session: DbSession,
) -> FunnelResponse:
    return await service.funnel(session, filters)


@router.get("/sources", response_model=SourcesResponse)
async def get_sources(
    filters: Filters,
    session: DbSession,
) -> SourcesResponse:
    return await service.sources(session, filters)


@router.get("/contact-channels", response_model=ContactChannelsResponse)
async def get_contact_channels(
    filters: Filters,
    session: DbSession,
) -> ContactChannelsResponse:
    return await service.contact_channels(session, filters)


@router.get("/products", response_model=ProductsResponse)
async def get_products(
    filters: Filters,
    session: DbSession,
) -> ProductsResponse:
    return await service.products(session, filters)


@router.get("/payment-methods", response_model=PaymentMethodsResponse)
async def get_payment_methods(
    filters: Filters,
    session: DbSession,
) -> PaymentMethodsResponse:
    return await service.payment_methods(session, filters)


@router.get("/period-comparison", response_model=PeriodComparisonResponse)
async def get_period_comparison(
    comparison: ComparisonQuery,
    session: DbSession,
) -> PeriodComparisonResponse:
    return await service.period_comparison(session, comparison)
