import time

from fastapi import Depends, Request

from core.config import settings
from domains.base.dependencies import require_ingest_access
from domains.base.exceptions import TooManyRequestsException
from domains.ingestion.sales_channels import resolve_request_origin

# key -> (window_id, count)
_store: dict[str, tuple[int, int]] = {}


def reset_rate_limit_store() -> None:
    _store.clear()


def rate_limit_store_size() -> int:
    return len(_store)


def rate_limit_store_keys() -> frozenset[str]:
    return frozenset(_store)


def _allowed_origins() -> set[str]:
    return {
        origin
        for channel in settings.sales_channels
        for origin in channel.origins
    }


def _client_key(request: Request) -> str:
    origin = resolve_request_origin(request)
    if origin is not None and origin in _allowed_origins():
        return f"origin:{origin}"
    if request.client is not None:
        return f"ip:{request.client.host}"
    return "ip:unknown"


def _retry_after(window_id: int, window_seconds: int, now: float) -> int:
    window_end = (window_id + 1) * window_seconds
    return max(1, int(window_end - now))


def _evict_expired(now: float, window_seconds: int) -> None:
    current_window = int(now // window_seconds)
    expired = [
        key
        for key, (window_id, _) in _store.items()
        if window_id != current_window
    ]
    for key in expired:
        del _store[key]


def _consume(
    key: str,
    limit: int,
    window_seconds: int,
    max_keys: int,
) -> int | None:
    now = time.time()
    _evict_expired(now, window_seconds)
    window_id = int(now // window_seconds)
    stored = _store.get(key)
    if stored is None:
        if len(_store) >= max_keys:
            return _retry_after(window_id, window_seconds, now)
        count = 0
        stored_window = window_id
    else:
        stored_window, count = stored
        if stored_window != window_id:
            stored_window, count = window_id, 0
    if count >= limit:
        return _retry_after(stored_window, window_seconds, now)
    _store[key] = (stored_window, count + 1)
    return None


async def enforce_ingest_rate_limit(
    request: Request,
    _: None = Depends(require_ingest_access),
) -> None:
    limit = settings.ingest_rate_limit
    # эта проверка нужна, чтобы мы могли отключить rate limit, переключая в конфиге на 0
    # например для тестирования
    if limit <= 0:
        return

    retry_after = _consume(
        _client_key(request),
        limit,
        settings.ingest_rate_limit_window_seconds,
        settings.ingest_rate_limit_max_keys,
    )
    if retry_after is not None:
        raise TooManyRequestsException(retry_after=retry_after)
