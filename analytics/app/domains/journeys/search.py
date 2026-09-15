import re
import uuid
from typing import Literal

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from domains.journeys.repository import list_events
from domains.journeys.schemas import (
    JourneyEntityType,
    JourneySearchHit,
    JourneySearchResponse,
)
from domains.projections.models.journal import Event
from domains.projections.parsing import event_payload

UUID_V4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
HEX32_RE = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)

SEARCH_SCAN_LIMIT = 500
SEARCH_HIT_LIMIT = 50
CONTACT_CHANNELS = frozenset({"form", "email", "whatsapp", "phone"})

SearchMode = Literal["uuid", "hex", "text"]

HEX_COLUMNS: tuple[tuple[JourneyEntityType, str], ...] = (
    ("lead", "lead_id"),
    ("order", "order_id"),
    ("customer", "customer_id"),
    ("contact", "contact_id"),
    ("manual_sale", "manual_sale_id"),
)


def classify_search_query(query: str) -> SearchMode:
    if UUID_V4_RE.fullmatch(query):
        return "uuid"
    if HEX32_RE.fullmatch(query):
        return "hex"
    return "text"


def _normalized_contact_channel(query: str) -> str | None:
    channel = query.lower()
    if channel in CONTACT_CHANNELS:
        return channel
    return None


def _payload_text(payload: dict, *keys: str) -> str | None:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    if isinstance(current, str):
        return current
    return None


def _hit(
    event: Event,
    entity_type: JourneyEntityType,
    entity_id: str,
) -> JourneySearchHit:
    return JourneySearchHit(
        entity_type=entity_type,
        id=entity_id,
        sales_channel_id=event.sales_channel_id,
        occurred_at=event.occurred_at,
    )


def _hits_for_event(event: Event, query: str, mode: SearchMode) -> list[JourneySearchHit]:
    if mode == "uuid":
        uid = uuid.UUID(query)
        hits: list[JourneySearchHit] = []
        if event.visitor_id == uid:
            hits.append(_hit(event, "visitor", str(event.visitor_id)))
        if event.session_id == uid:
            hits.append(_hit(event, "session", str(event.session_id)))
        return hits

    if mode == "hex":
        hex_id = query.lower()
        return [
            _hit(event, entity_type, hex_id)
            for entity_type, column in HEX_COLUMNS
            if getattr(event, column) == hex_id
        ]

    payload = event_payload(event)
    hits = []
    if _payload_text(payload, "order_number") == query and event.order_id:
        hits.append(_hit(event, "order", event.order_id))
    click_ids = payload.get("click_ids")
    if isinstance(click_ids, dict) and event.visitor_id is not None:
        if query in (
            click_ids.get("gclid"),
            click_ids.get("gbraid"),
            click_ids.get("wbraid"),
        ):
            hits.append(_hit(event, "visitor", str(event.visitor_id)))
    if _payload_text(payload, "tracking_reference") == query and event.contact_id:
        hits.append(_hit(event, "contact", event.contact_id))
    if _payload_text(payload, "utm", "utm_campaign") == query and event.visitor_id:
        hits.append(_hit(event, "visitor", str(event.visitor_id)))
    channel = _normalized_contact_channel(query)
    if channel is not None and channel in {
        _payload_text(payload, "contact_channel"),
        _payload_text(payload, "channel"),
    }:
        if event.contact_id:
            hits.append(_hit(event, "contact", event.contact_id))
        if event.lead_id:
            hits.append(_hit(event, "lead", event.lead_id))
        if (
            event.visitor_id is not None
            and event.contact_id is None
            and event.lead_id is None
        ):
            hits.append(_hit(event, "visitor", str(event.visitor_id)))
    return hits


def _search_clause(query: str, mode: SearchMode):
    if mode == "uuid":
        uid = uuid.UUID(query)
        return or_(Event.visitor_id == uid, Event.session_id == uid)

    if mode == "hex":
        hex_id = query.lower()
        return or_(
            Event.lead_id == hex_id,
            Event.order_id == hex_id,
            Event.customer_id == hex_id,
            Event.contact_id == hex_id,
            Event.manual_sale_id == hex_id,
        )

    payload = Event.body["payload"]
    clauses = [
        payload["order_number"].as_string() == query,
        payload["click_ids"]["gclid"].as_string() == query,
        payload["click_ids"]["gbraid"].as_string() == query,
        payload["click_ids"]["wbraid"].as_string() == query,
        payload["tracking_reference"].as_string() == query,
        payload["utm"]["utm_campaign"].as_string() == query,
    ]
    channel = _normalized_contact_channel(query)
    if channel is not None:
        clauses.extend(
            (
                payload["contact_channel"].as_string() == channel,
                payload["channel"].as_string() == channel,
            )
        )
    return or_(*clauses)


async def search_journeys(
    session: AsyncSession,
    query: str,
) -> JourneySearchResponse:
    mode = classify_search_query(query)
    events = await list_events(
        session,
        _search_clause(query, mode),
        limit=SEARCH_SCAN_LIMIT,
    )
    seen: dict[tuple[str, str], JourneySearchHit] = {}
    for event in events:
        for hit in _hits_for_event(event, query, mode):
            key = (hit.entity_type, hit.id)
            if key not in seen:
                seen[key] = hit
            if len(seen) >= SEARCH_HIT_LIMIT:
                return JourneySearchResponse(items=list(seen.values()))
    return JourneySearchResponse(items=list(seen.values()))
