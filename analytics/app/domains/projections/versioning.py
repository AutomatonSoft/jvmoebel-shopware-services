from datetime import datetime


def should_apply_entity_update(
    *,
    is_stub: bool,
    stored_aggregate_version: int | None,
    incoming_aggregate_version: int | None,
    stored_occurred_at: datetime | None,
    incoming_occurred_at: datetime,
    has_version_column: bool,
    allow_equal: bool = False,
) -> bool:
    if is_stub:
        return True

    if has_version_column:
        if stored_aggregate_version is None:
            return True
        if incoming_aggregate_version is not None:
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

    if stored_occurred_at is None:
        return True
    if incoming_occurred_at > stored_occurred_at:
        return True
    return allow_equal and incoming_occurred_at == stored_occurred_at
