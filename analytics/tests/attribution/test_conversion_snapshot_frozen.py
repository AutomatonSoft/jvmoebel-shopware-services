from copy import deepcopy
from uuid import uuid4

from domains.projections.models.entities import Lead, ManualSale


async def test_late_session_does_not_refresh_lead_snapshot(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    db_session,
) -> None:
    first = deepcopy(session_started_event)
    first["event_id"] = str(uuid4())
    first["occurred_at"] = "2026-08-24T08:00:00Z"
    first["payload"]["utm"]["utm_campaign"] = "campaign-a"
    await persist_event(first)

    created = load_shopware_event("lead-created")
    created["visitor_id"] = session_started_event["visitor_id"]
    created["session_id"] = first["session_id"]
    created["occurred_at"] = "2026-08-24T10:00:00Z"
    await persist_event(created)

    later = deepcopy(session_started_event)
    later["event_id"] = str(uuid4())
    later["session_id"] = str(uuid4())
    later["occurred_at"] = "2026-08-24T12:00:00Z"
    later["payload"]["utm"]["utm_campaign"] = "campaign-b"
    await persist_event(later)

    late_early = deepcopy(session_started_event)
    late_early["event_id"] = str(uuid4())
    late_early["session_id"] = str(uuid4())
    late_early["occurred_at"] = "2026-08-24T09:00:00Z"
    late_early["payload"]["utm"]["utm_campaign"] = "campaign-late-early"
    await persist_event(late_early)

    lead = await db_session.get(Lead, created["lead_id"])
    assert lead is not None
    assert lead.attr_last_non_direct_utm_campaign == "campaign-a"
    assert lead.attr_first_touch_utm_campaign == "campaign-a"


async def test_late_session_does_not_refresh_manual_sale_snapshot(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    db_session,
) -> None:
    first = deepcopy(session_started_event)
    first["event_id"] = str(uuid4())
    first["occurred_at"] = "2026-08-24T08:00:00Z"
    first["payload"]["utm"]["utm_campaign"] = "campaign-a"
    await persist_event(first)

    created = load_shopware_event("manual-sale-created")
    created["visitor_id"] = session_started_event["visitor_id"]
    created["occurred_at"] = "2026-08-24T10:00:00Z"
    created["payload"]["confirmed_at"] = "2026-08-24T10:00:00Z"
    await persist_event(created)

    later = deepcopy(session_started_event)
    later["event_id"] = str(uuid4())
    later["session_id"] = str(uuid4())
    later["occurred_at"] = "2026-08-24T12:00:00Z"
    later["payload"]["utm"]["utm_campaign"] = "campaign-b"
    await persist_event(later)

    late_early = deepcopy(session_started_event)
    late_early["event_id"] = str(uuid4())
    late_early["session_id"] = str(uuid4())
    late_early["occurred_at"] = "2026-08-24T09:00:00Z"
    late_early["payload"]["utm"]["utm_campaign"] = "campaign-late-early"
    await persist_event(late_early)

    sale = await db_session.get(ManualSale, created["manual_sale_id"])
    assert sale is not None
    assert sale.attr_last_non_direct_utm_campaign == "campaign-a"
    assert sale.attr_first_touch_utm_campaign == "campaign-a"
