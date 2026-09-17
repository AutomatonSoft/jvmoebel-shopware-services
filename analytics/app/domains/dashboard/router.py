from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import get_async_session
from domains.dashboard.auth import require_dashboard_access
from domains.dashboard.filters import (
    datetime_local_value,
    filter_query_string,
    parse_dashboard_filters,
)
from domains.dashboard.journey import journey_clause
from domains.dashboard.templating import templates
from domains.journeys.repository import load_journey
from domains.journeys.search import search_journeys
from domains.reports import service
from domains.reports.filters import ReportFilters

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_dashboard_access)],
    include_in_schema=False,
)

DbSession = Annotated[AsyncSession, Depends(get_async_session)]
Filters = Annotated[ReportFilters, Depends(parse_dashboard_filters)]


def _page_context(
    request: Request,
    filters: ReportFilters,
    **extra: object,
) -> dict[str, object]:
    return {
        "request": request,
        "filters": filters,
        "filter_qs": filter_query_string(filters),
        "period_from_value": datetime_local_value(filters.period_from),
        "period_to_value": datetime_local_value(filters.period_to),
        **extra,
    }


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def overview_page(
    request: Request,
    filters: Filters,
    session: DbSession,
) -> HTMLResponse:
    overview = await service.overview(session, filters)
    return templates.TemplateResponse(
        request,
        "overview.html",
        _page_context(request, filters, overview=overview, page="overview"),
    )


@router.get("/funnel", response_class=HTMLResponse)
async def funnel_page(
    request: Request,
    filters: Filters,
    session: DbSession,
) -> HTMLResponse:
    funnel = await service.funnel(session, filters)
    is_empty = all(step.count == 0 for step in (*funnel.ecommerce, *funnel.lead))
    return templates.TemplateResponse(
        request,
        "funnel.html",
        _page_context(
            request,
            filters,
            funnel=funnel,
            page="funnel",
            is_empty=is_empty,
        ),
    )


@router.get("/sources", response_class=HTMLResponse)
async def sources_page(
    request: Request,
    filters: Filters,
    session: DbSession,
) -> HTMLResponse:
    sources = await service.sources(session, filters)
    return templates.TemplateResponse(
        request,
        "sources.html",
        _page_context(request, filters, sources=sources, page="sources"),
    )


@router.get("/journey", response_class=HTMLResponse)
async def journey_search_page(
    request: Request,
    filters: Filters,
    session: DbSession,
    q: Annotated[str | None, Query()] = None,
) -> HTMLResponse:
    query = q.strip() if q else ""
    hits = []
    if query:
        result = await search_journeys(session, query)
        hits = result.items
    return templates.TemplateResponse(
        request,
        "journey_search.html",
        _page_context(
            request,
            filters,
            page="journey",
            q=query,
            hits=hits,
        ),
    )


@router.get("/journey/{entity_type}/{entity_id}", response_class=HTMLResponse)
async def journey_detail_page(
    request: Request,
    entity_type: str,
    entity_id: str,
    filters: Filters,
    session: DbSession,
) -> HTMLResponse:
    journey = await load_journey(session, journey_clause(entity_type, entity_id))
    return templates.TemplateResponse(
        request,
        "journey.html",
        _page_context(
            request,
            filters,
            page="journey",
            entity_type=entity_type,
            entity_id=entity_id,
            events=journey.events,
        ),
    )
