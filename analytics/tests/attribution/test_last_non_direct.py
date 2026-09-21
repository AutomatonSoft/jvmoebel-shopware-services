from copy import deepcopy
from uuid import UUID, uuid4

from domains.projections.models.entities import Session, Visitor


def _later_session(session_started_event: dict, referrer: str) -> dict:
    later = deepcopy(session_started_event)
    later["event_id"] = str(uuid4())
    later["session_id"] = str(uuid4())
    later["occurred_at"] = "2026-08-24T15:00:00Z"
    later["payload"].pop("utm", None)
    later["payload"].pop("click_ids", None)
    later["payload"]["referrer"] = referrer
    return later


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


async def test_payment_referrer_does_not_move_last_non_direct(
    persist_event,
    session_started_event: dict,
    db_session,
) -> None:
    await persist_event(deepcopy(session_started_event))
    paypal = _later_session(
        session_started_event,
        "https://www.paypal.com/checkoutnow",
    )
    await persist_event(paypal)

    visitor = await db_session.get(
        Visitor,
        session_started_event["visitor_id"],
    )
    session_row = await db_session.get(Session, UUID(paypal["session_id"]))
    assert visitor is not None
    assert session_row is not None
    assert visitor.last_non_direct_source == "google_ads"
    assert visitor.first_touch_source == "google_ads"
    assert session_row.source == "direct"


async def test_own_shop_referrer_does_not_move_last_non_direct(
    persist_event,
    session_started_event: dict,
    db_session,
) -> None:
    await persist_event(deepcopy(session_started_event))
    own = _later_session(
        session_started_event,
        "https://www.jvmoebel.de/checkout/return",
    )
    await persist_event(own)

    visitor = await db_session.get(
        Visitor,
        session_started_event["visitor_id"],
    )
    session_row = await db_session.get(Session, UUID(own["session_id"]))
    assert visitor is not None
    assert session_row is not None
    assert visitor.last_non_direct_source == "google_ads"
    assert session_row.source == "direct"


async def test_external_referral_updates_last_non_direct(
    persist_event,
    session_started_event: dict,
    db_session,
) -> None:
    await persist_event(deepcopy(session_started_event))
    referral = _later_session(session_started_event, "https://example.com/blog")
    await persist_event(referral)

    visitor = await db_session.get(
        Visitor,
        session_started_event["visitor_id"],
    )
    session_row = await db_session.get(Session, UUID(referral["session_id"]))
    assert visitor is not None
    assert session_row is not None
    assert visitor.last_non_direct_source == "referral"
    assert session_row.source == "referral"
