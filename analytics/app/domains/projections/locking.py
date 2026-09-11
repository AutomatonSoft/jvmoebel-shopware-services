from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from core.db.postgres import Base
from domains.projections.exceptions import require_row

T = TypeVar("T", bound=Base)


async def get_aggregate_for_update(
    session: AsyncSession,
    model: type[T],
    pk: str,
    *,
    entity: str,
    event_type: str,
) -> T:
    row = await session.get(
        model,
        pk,
        with_for_update=True,
        populate_existing=True,
    )
    return require_row(
        row,
        entity=entity,
        event_type=event_type,
    )
