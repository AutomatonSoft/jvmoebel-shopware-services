from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from domains.attribution.classifier import classify_source
from domains.attribution.rules import Touch, apply_first_touch, apply_last_non_direct
from domains.attribution.service import refresh_dependent_snapshots
from domains.projections.exceptions import require_id, require_row
from domains.projections.models.entities import Session, Visitor
from domains.projections.models.facts import AttributionTouch
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload
from domains.projections.versioning import should_apply_entity_update


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


async def handle_session_started(
    session: AsyncSession,
    event: Event,
) -> None:
    visitor_id = require_id(
        event.visitor_id,
        field="visitor_id",
        event_type=event.event_type,
    )
    session_id = require_id(
        event.session_id,
        field="session_id",
        event_type=event.event_type,
    )

    visitor = require_row(
        await session.get(Visitor, visitor_id),
        entity="visitor",
        event_type=event.event_type,
    )
    row = require_row(
        await session.get(Session, session_id),
        entity="session",
        event_type=event.event_type,
    )

    payload = event_payload(event)
    raw_utm = payload.get("utm")
    utm = raw_utm if isinstance(raw_utm, dict) else {}
    raw_click_ids = payload.get("click_ids")
    click_ids = raw_click_ids if isinstance(raw_click_ids, dict) else {}

    utm_source = _optional_str(utm.get("utm_source"))
    utm_medium = _optional_str(utm.get("utm_medium"))
    utm_campaign = _optional_str(utm.get("utm_campaign"))
    utm_content = _optional_str(utm.get("utm_content"))
    utm_term = _optional_str(utm.get("utm_term"))
    gclid = _optional_str(click_ids.get("gclid"))
    gbraid = _optional_str(click_ids.get("gbraid"))
    wbraid = _optional_str(click_ids.get("wbraid"))
    landing_page = _optional_str(payload.get("landing_page"))
    referrer = _optional_str(payload.get("referrer"))
    source = classify_source(
        gclid=gclid,
        gbraid=gbraid,
        wbraid=wbraid,
        utm_source=utm_source,
        utm_medium=utm_medium,
        referrer=referrer,
    )

    if not should_apply_entity_update(
        is_stub=row.is_stub,
        stored_aggregate_version=None,
        incoming_aggregate_version=None,
        stored_occurred_at=row.last_event_occurred_at,
        incoming_occurred_at=event.occurred_at,
        has_version_column=False,
    ):
        return

    row.visitor_id = visitor_id
    row.sales_channel_id = event.sales_channel_id
    row.market_code = event.market_code
    row.occurred_at = event.occurred_at
    row.landing_page = landing_page
    row.referrer = referrer
    row.domain = event.domain
    row.utm_source = utm_source
    row.utm_medium = utm_medium
    row.utm_campaign = utm_campaign
    row.utm_content = utm_content
    row.utm_term = utm_term
    row.gclid = gclid
    row.gbraid = gbraid
    row.wbraid = wbraid
    row.source = source
    row.event_id = event.event_id
    row.is_stub = False
    row.last_event_occurred_at = event.occurred_at

    visitor.is_stub = False
    if visitor.first_seen_at is None or event.occurred_at < visitor.first_seen_at:
        visitor.first_seen_at = event.occurred_at
    if visitor.last_seen_at is None or event.occurred_at > visitor.last_seen_at:
        visitor.last_seen_at = event.occurred_at
    visitor.last_event_occurred_at = _max_datetime(
        visitor.last_event_occurred_at,
        event.occurred_at,
    )

    touch = Touch(
        source=source,
        occurred_at=event.occurred_at,
        sales_channel_id=event.sales_channel_id,
        campaign=utm_campaign,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        utm_content=utm_content,
        utm_term=utm_term,
        gclid=gclid,
        gbraid=gbraid,
        wbraid=wbraid,
        landing_page=landing_page,
        referrer=referrer,
    )
    apply_first_touch(visitor, touch)
    apply_last_non_direct(visitor, touch)

    session.add(
        AttributionTouch(
            event_id=event.event_id,
            visitor_id=visitor_id,
            session_id=session_id,
            sales_channel_id=event.sales_channel_id,
            occurred_at=event.occurred_at,
            source=source,
            campaign=utm_campaign,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            gclid=gclid,
            gbraid=gbraid,
            wbraid=wbraid,
            landing_page=landing_page,
            referrer=referrer,
            is_direct=touch.is_direct,
        )
    )
    await refresh_dependent_snapshots(session, visitor, event.occurred_at)


def _max_datetime(
    left: datetime | None,
    right: datetime,
) -> datetime:
    if left is None or right > left:
        return right
    return left
