from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import get_async_session
from domains.base.dependencies import require_read_access
from domains.journeys.dependencies import VisitorId
from domains.visitors.schemas import AnonymizeVisitorResponse
from domains.visitors.service import anonymize_visitor

router = APIRouter(
    prefix="/analytics",
    tags=["Visitors"],
    dependencies=[Depends(require_read_access)],
)

DbSession = Annotated[AsyncSession, Depends(get_async_session)]

ANONYMIZE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "description": "Missing or invalid read API key",
    },
    404: {
        "description": "Visitor not found",
    },
    422: {
        "description": "Invalid path identifier",
    },
}


@router.post(
    "/visitors/{visitor_id}/anonymize",
    response_model=AnonymizeVisitorResponse,
    responses=ANONYMIZE_RESPONSES,
)
async def post_anonymize_visitor(
    visitor_id: VisitorId,
    session: DbSession,
) -> AnonymizeVisitorResponse:
    return await anonymize_visitor(session, visitor_id)
