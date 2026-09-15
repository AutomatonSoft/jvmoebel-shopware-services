from copy import deepcopy
from uuid import uuid4

from domains.projections.models.entities import Visitor


async def test_direct_does_not_move_last_non_direct(
    persist_event,
    session_started_event: dict,
    db_session,
) -> None:
    ads = deepcopy(session_started_event)
    await persist_event(ads)

    direct = deepcopy(session_started_event)
    direct["event_id"] = str(uuid4())
    direct["session_id"] = str(uuid4())
    direct["occurred_at"] = "2026-08-24T15:00:00Z"
    direct["payload"].pop("utm", None)
    direct["payload"].pop("click_ids", None)
    direct["payload"].pop("referrer", None)

    await persist_event(direct)

    visitor = await db_session.get(
        Visitor,
        session_started_event["visitor_id"],
    )
    assert visitor is not None
    assert visitor.last_non_direct_source == "google_ads"
    assert visitor.first_touch_source == "google_ads"
