import time

from fastapi import Request

from core.config import settings
from domains.base.exceptions import TooManyRequestsException
from domains.ingestion.sales_channels import resolve_request_origin

# key -> (window_id, count)
_store: dict[str, tuple[int, int]] = {}


def reset_rate_limit_store() -> None:
    _store.clear()


def _client_key(request: Request) -> str:
    origin = resolve_request_origin(request)
    if origin is not None:
        return origin
    if request.client is not None:
        return request.client.host
    return "unknown"


def _consume(key: str, limit: int, window_seconds: int) -> int | None:
    now = time.time()
    window_id = int(now // window_seconds)
    stored_window, count = _store.get(key, (window_id, 0))
    if stored_window != window_id:
        stored_window, count = window_id, 0
    if count >= limit:
        window_end = (window_id + 1) * window_seconds
        return max(1, int(window_end - now))
    _store[key] = (stored_window, count + 1)
    return None


def enforce_ingest_rate_limit(request: Request) -> None:
    limit = settings.ingest_rate_limit
    # эта проверка нужна, чтобы мы могли отключить rate limit, переключая в конфиге на 0
    # например для тестирования
    if limit <= 0:
        return
        
    retry_after = _consume(
        _client_key(request),
        limit,
        settings.ingest_rate_limit_window_seconds,
    )
    if retry_after is not None:
        raise TooManyRequestsException(retry_after=retry_after)
