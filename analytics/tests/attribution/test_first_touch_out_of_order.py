from copy import deepcopy
from uuid import uuid4

from domains.projections.models.entities import Visitor


async def test_first_touch_uses_earliest_occurred_at(
    persist_event,
    session_started_event: dict,
    db_session,
) -> None:
    later = deepcopy(session_started_event)
    later["event_id"] = str(uuid4())
    later["session_id"] = str(uuid4())
    later["occurred_at"] = "2026-08-24T12:00:00Z"
    later["payload"]["utm"]["utm_campaign"] = "later-campaign"

    earlier = deepcopy(session_started_event)
    earlier["event_id"] = str(uuid4())
    earlier["session_id"] = str(uuid4())
    earlier["occurred_at"] = "2026-08-24T08:00:00Z"
    earlier["payload"]["utm"]["utm_campaign"] = "earlier-campaign"

    await persist_event(later)
    await persist_event(earlier)

    visitor = await db_session.get(
        Visitor,
        session_started_event["visitor_id"],
    )
    assert visitor is not None
    assert visitor.first_touch_utm_campaign == "earlier-campaign"
    assert visitor.first_touch_occurred_at.isoformat().startswith("2026-08-24T08:00:00")
