from domains.projections.models.entities import Lead


async def test_lead_gets_full_visitor_attribution_snapshot(
    persist_event,
    session_started_event: dict,
    load_shopware_event,
    db_session,
) -> None:
    await persist_event(session_started_event)
    created = load_shopware_event("lead-created")
    created["visitor_id"] = session_started_event["visitor_id"]
    created["session_id"] = session_started_event["session_id"]
    await persist_event(created)

    lead = await db_session.get(Lead, created["lead_id"])
    assert lead is not None
    assert lead.attr_first_touch_source == "google_ads"
    assert lead.attr_first_touch_gclid == "Cj0KCQjw-example"
    assert lead.attr_first_touch_utm_source == "google"
    assert lead.attr_first_touch_utm_medium == "cpc"
    assert lead.attr_first_touch_utm_campaign == "sofas-de-2026"
    assert lead.attr_first_touch_landing_page is not None
    assert lead.attr_first_touch_referrer is not None
    assert lead.attr_first_touch_sales_channel_id == created["sales_channel_id"]
    assert lead.attr_last_non_direct_source == "google_ads"
