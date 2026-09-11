from urllib.parse import urlsplit

from fastapi import Request

from core.config import SalesChannelSettings, settings
from domains.ingestion.exceptions import EventValidationError


def get_sales_channel(
    sales_channel_id: str,
) -> SalesChannelSettings | None:
    for channel in settings.sales_channels:
        if channel.id == sales_channel_id:
            return channel
    return None


def resolve_request_origin(request: Request) -> str | None:
    # стандартный HTTP-заголовок: «с какого сайта ушёл запрос». Браузер ставит его сам,
    # например https://www.jvmoebel.de
    origin = request.headers.get("origin")

    if origin:
        return origin

    # стандартный HTTP-заголовок: «с какой страницы ушёл запрос». Браузер ставит его сам,
    # например https://www.jvmoebel.de/sofas/sofa-001
    referer = request.headers.get("referer")

    if referer is None:
        return None

    # разбиваем URL на части: scheme - протокол, netloc - домен и порт
    parts = urlsplit(referer)
    if not parts.scheme or not parts.netloc:
        return None

    return f"{parts.scheme}://{parts.netloc}"


def _require_known_channel(
    sales_channel_id: str,
    *,
    market_code: str | None,
) -> SalesChannelSettings:
    channel = get_sales_channel(sales_channel_id)
    if channel is None:
        raise EventValidationError(
            detail="Unknown sales_channel_id",
        )

    if market_code is not None and market_code != channel.market_code:
        raise EventValidationError(
            detail="market_code does not match sales channel",
        )
    return channel


def _origin_hostname(origin: str) -> str | None:
    host = urlsplit(origin).hostname
    if host is None or not host:
        return None
    return host.lower()


def _event_hostname(domain: str) -> str:
    value = domain.strip().lower()
    if "://" in value:
        host = urlsplit(value).hostname
        if host:
            return host.lower()
    return value.split("/")[0].split(":")[0]


def assert_http_channel_allowed(
    sales_channel_id: str,
    *,
    origin: str | None,
    market_code: str | None,
    domain: str | None,
) -> None:
    channel = _require_known_channel(
        sales_channel_id,
        market_code=market_code,
    )

    if origin is None or origin not in channel.origins:
        raise EventValidationError(
            detail="Origin is not allowed for this sales channel",
        )

    if domain is None:
        return
    allowed_hosts = {
        host
        for channel_origin in channel.origins
        if (host := _origin_hostname(channel_origin)) is not None
    }
    if _event_hostname(domain) not in allowed_hosts:
        raise EventValidationError(
            detail="domain is not allowed for this sales channel",
        )


def assert_rabbit_channel_allowed(
    sales_channel_id: str,
    *,
    market_code: str | None,
) -> None:
    _require_known_channel(
        sales_channel_id,
        market_code=market_code,
    )
