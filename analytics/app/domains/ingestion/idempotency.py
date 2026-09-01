from sqlalchemy.exc import IntegrityError

EVENT_ID_CONSTRAINTS = frozenset({"events_pkey"}) # postgres сам так называет первичный ключ в таблице events


def is_event_id_unique_violation(exc: IntegrityError) -> bool:
    orig = exc.orig # достаем оригинальную ошибку asyncpg/Postgres (UniqueViolationError)
    constraint_name = getattr(orig, "constraint_name", None)
    # если имя совпало с PK журнала - это повтор
    if constraint_name in EVENT_ID_CONSTRAINTS:
        return True

    return "events_pkey" in str(orig or exc)
