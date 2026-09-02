from datetime import datetime
from decimal import Decimal

from domains.projections.models.journal import Event


def parse_datetime(value: str) -> datetime:
    # Контракт шлёт RFC3339 с суффиксом Z (UTC), например 2026-08-24T09:00:00Z.
    # datetime.fromisoformat до версии Python 3.11 не принимает Z, только смещение +00:00.
    # Без tzinfo сравнение occurred_at с timestamptz в Postgres падает.
    # В Python 3.11+ можно просто return datetime.fromisoformat(value) но на всякий случай добавил replace
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_money(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def event_payload(event: Event) -> dict:
    payload = event.body.get("payload")
    if isinstance(payload, dict):
        return payload
    return {}
