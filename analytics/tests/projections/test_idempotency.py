from sqlalchemy import func, select

from domains.projections.models.facts import ProductView
from domains.projections.models.journal import Event


async def test_repeat_event_does_not_project_twice(
    persist_event,
    session_started_event: dict,
    db_session,
) -> None:
    first = await persist_event(session_started_event)
    second = await persist_event(session_started_event)
    assert first == "accepted"
    assert second == "duplicate"

    events = await db_session.scalar(select(func.count()).select_from(Event))
    views = await db_session.scalar(select(func.count()).select_from(ProductView))
    assert events == 1
    assert views == 0
