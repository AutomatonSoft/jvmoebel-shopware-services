from typing import TypeVar

T = TypeVar("T")


class ProjectionInvariantError(RuntimeError):
    """Handler cannot project; ingest TX must ROLLBACK."""


def require_id(value: T | None, *, field: str, event_type: str) -> T:
    if value is None:
        raise ProjectionInvariantError(
            f"{event_type} missing required {field}"
        )
    return value


def require_row(row: T | None, *, entity: str, event_type: str) -> T:
    if row is None:
        raise ProjectionInvariantError(
            f"{event_type}: {entity} row missing after stubs"
        )
    return row
