import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

JourneyEntityType = Literal[
    "visitor",
    "session",
    "lead",
    "order",
    "customer",
    "contact",
    "manual_sale",
]


class JourneyEvent(BaseModel):
    event_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    received_at: datetime
    source: str
    sales_channel_id: str
    visitor_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    lead_id: str | None = None
    customer_id: str | None = None
    order_id: str | None = None
    contact_id: str | None = None
    manual_sale_id: str | None = None
    refund_id: str | None = None
    payload: dict[str, Any]


class JourneyResponse(BaseModel):
    events: list[JourneyEvent]


class JourneySearchHit(BaseModel):
    entity_type: JourneyEntityType
    id: str
    sales_channel_id: str
    occurred_at: datetime


class JourneySearchResponse(BaseModel):
    items: list[JourneySearchHit]
