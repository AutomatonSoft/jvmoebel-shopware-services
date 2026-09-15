from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import get_async_session
from domains.base.dependencies import require_read_access
from domains.journeys.scope import (
    customer_events_clause,
    lead_events_clause,
    order_events_clause,
)
from domains.journeys.dependencies import PathEntityId, VisitorId, parse_search_query
from domains.journeys.repository import load_journey
from domains.journeys.schemas import JourneyResponse, JourneySearchResponse
from domains.journeys.search import search_journeys
from domains.projections.models.journal import Event

router = APIRouter(
    prefix="/analytics",
    tags=["Journeys"],
    dependencies=[Depends(require_read_access)],
)

DbSession = Annotated[AsyncSession, Depends(get_async_session)]

JOURNEY_SEARCH_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "q is required",
    },
    401: {
        "description": "Missing or invalid read API key",
    },
    422: {
        "description": "Invalid query parameter",
    },
}

JOURNEY_ENTITY_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "description": "Missing or invalid read API key",
    },
    404: {
        "description": "Journey not found",
    },
    422: {
        "description": "Invalid path identifier",
    },
}


@router.get(
    "/journey/search",
    response_model=JourneySearchResponse,
    responses=JOURNEY_SEARCH_RESPONSES,
)
async def get_journey_search(
    session: DbSession,
    q: Annotated[str, Depends(parse_search_query)],
) -> JourneySearchResponse:
    return await search_journeys(session, q)


@router.get(
    "/visitors/{visitor_id}/journey",
    response_model=JourneyResponse,
    responses=JOURNEY_ENTITY_RESPONSES,
)
async def get_visitor_journey(
    visitor_id: VisitorId,
    session: DbSession,
) -> JourneyResponse:
    return await load_journey(session, Event.visitor_id == visitor_id)


@router.get(
    "/leads/{lead_id}/journey",
    response_model=JourneyResponse,
    responses=JOURNEY_ENTITY_RESPONSES,
)
async def get_lead_journey(
    lead_id: PathEntityId,
    session: DbSession,
) -> JourneyResponse:
    return await load_journey(session, lead_events_clause(lead_id.lower()))


@router.get(
    "/orders/{order_id}/journey",
    response_model=JourneyResponse,
    responses=JOURNEY_ENTITY_RESPONSES,
)
async def get_order_journey(
    order_id: PathEntityId,
    session: DbSession,
) -> JourneyResponse:
    return await load_journey(session, order_events_clause(order_id.lower()))


@router.get(
    "/customers/{customer_id}/journey",
    response_model=JourneyResponse,
    responses=JOURNEY_ENTITY_RESPONSES,
)
async def get_customer_journey(
    customer_id: PathEntityId,
    session: DbSession,
) -> JourneyResponse:
    return await load_journey(
        session,
        customer_events_clause(customer_id.lower()),
    )
