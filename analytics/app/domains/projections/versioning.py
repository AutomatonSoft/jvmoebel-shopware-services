from datetime import datetime

from domains.projections.models.journal import Event


def order_identity_values(event: Event, payload: dict) -> dict[str, object]:
    return {
        "order_number": payload.get("order_number"),
        "visitor_id": event.visitor_id,
        "session_id": event.session_id,
        "cart_id": event.cart_id,
        "lead_id": event.lead_id,
        "customer_id": event.customer_id,
        "sales_channel_id": event.sales_channel_id,
        "market_code": event.market_code,
        "payment_method": payload.get("payment_method"),
        "currency": payload.get("currency"),
    }


def should_apply_entity_update(
    *,
    stored_aggregate_version: int | None,
    incoming_aggregate_version: int | None,
    stored_occurred_at: datetime | None,
    incoming_occurred_at: datetime,
    has_version_column: bool,
    allow_equal: bool = False,
) -> bool:
    # Пустая проекция: ещё не было ни version, ни occurred_at.
    # is_stub больше не обходит сравнение — иначе поздний created откатывает статус.
    if stored_aggregate_version is None and stored_occurred_at is None:
        return True

    if (
        has_version_column
        and stored_aggregate_version is not None
        and incoming_aggregate_version is not None
    ):
        if incoming_aggregate_version > stored_aggregate_version:
            return True
        return (
            allow_equal
            and incoming_aggregate_version == stored_aggregate_version
        )

    if stored_occurred_at is None:
        return True
    if incoming_occurred_at > stored_occurred_at:
        return True
    return allow_equal and incoming_occurred_at == stored_occurred_at


def overlay_attributes(
    entity: object,
    values: dict[str, object],
    *,
    only_empty: bool,
) -> None:
    for attr, value in values.items():
        if value is None:
            continue
        if only_empty and getattr(entity, attr) is not None:
            continue
        setattr(entity, attr, value)
