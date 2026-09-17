from uuid import UUID

from sqlalchemy import ColumnElement

from domains.base.exceptions import NotFoundException
from domains.journeys.scope import (
    customer_events_clause,
    lead_events_clause,
    order_events_clause,
)
from domains.projections.models.journal import Event

ENTITY_TYPES: frozenset[str] = frozenset(
    {
        "visitor",
        "session",
        "lead",
        "order",
        "customer",
        "contact",
        "manual_sale",
    }
)


def journey_clause(entity_type: str, entity_id: str) -> ColumnElement[bool]:
    if entity_type not in ENTITY_TYPES:
        raise NotFoundException(detail="Journey not found")
    try:
        if entity_type == "visitor":
            return Event.visitor_id == UUID(entity_id)
        if entity_type == "session":
            return Event.session_id == UUID(entity_id)
    except ValueError as exc:
        raise NotFoundException(detail="Journey not found") from exc

    hex_id = entity_id.lower()
    if entity_type == "lead":
        return lead_events_clause(hex_id)
    if entity_type == "order":
        return order_events_clause(hex_id)
    if entity_type == "customer":
        return customer_events_clause(hex_id)
    if entity_type == "contact":
        return Event.contact_id == hex_id
    return Event.manual_sale_id == hex_id
