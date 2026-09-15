from typing import Annotated
from uuid import UUID

from fastapi import Path, Query

from domains.base.exceptions import BadRequestException

PATH_ENTITY_ID_PATTERN = r"^[0-9a-fA-F]{32}$"

PathEntityId = Annotated[
    str,
    Path(min_length=32, max_length=32, pattern=PATH_ENTITY_ID_PATTERN),
]
VisitorId = Annotated[UUID, Path()]


def parse_search_query(q: Annotated[str, Query(min_length=1)]) -> str:
    query = q.strip()
    if not query:
        raise BadRequestException(detail="q is required")
    return query
