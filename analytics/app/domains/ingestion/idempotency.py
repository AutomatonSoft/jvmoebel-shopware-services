import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from domains.projections.models.journal import Event

EVENT_ID_CONSTRAINTS = frozenset({"events_pkey"})  # postgres сам так называет первичный ключ в таблице events

_IDENTITY_FIELDS = (
    "event_type",
    "event_version",
    "occurred_at",
    "source",
    "sales_channel_id",
    "market_code",
    "domain",
    "language",
    "visitor_id",
    "session_id",
    "cart_id",
    "lead_id",
    "customer_id",
    "order_id",
    "contact_id",
    "manual_sale_id",
    "refund_id",
    "aggregate_type",
    "aggregate_id",
    "aggregate_version",
    "correlation_id",
    "consent",
)


def is_event_id_unique_violation(exc: IntegrityError) -> bool:
    orig = exc.orig  # достаем оригинальную ошибку asyncpg/Postgres (UniqueViolationError)
    constraint_name = getattr(orig, "constraint_name", None)
    # если имя совпало с PK журнала - это повтор
    if constraint_name in EVENT_ID_CONSTRAINTS:
        return True

    return "events_pkey" in str(orig or exc)


def _normalize(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return value


def _identity(values: dict, payload: object) -> tuple[object, ...]:
    fields = tuple(_normalize(values.get(field)) for field in _IDENTITY_FIELDS)
    return fields + (_normalize(payload if payload is not None else {}),)


def is_same_event(stored: Event, incoming_values: dict) -> bool:
    stored_values = {field: getattr(stored, field) for field in _IDENTITY_FIELDS}
    stored_payload = None
    if isinstance(stored.body, dict):
        stored_payload = stored.body.get("payload")
    incoming_body = incoming_values.get("body")
    incoming_payload = None
    if isinstance(incoming_body, dict):
        incoming_payload = incoming_body.get("payload")
    return _identity(stored_values, stored_payload) == _identity(
        incoming_values,
        incoming_payload,
    )
