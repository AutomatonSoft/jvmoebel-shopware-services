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


def assert_http_channel_allowed(
    sales_channel_id: str,
    *,
    origin: str | None,
    market_code: str | None,
) -> None:
    channel = get_sales_channel(sales_channel_id)
    if channel is None:
        raise EventValidationError(
            detail="Unknown sales_channel_id",
        )

    if origin is None or origin not in channel.origins:
        raise EventValidationError(
            detail="Origin is not allowed for this sales channel",
        )

    if (
        market_code is not None
        and market_code != channel.market_code
    ):
        raise EventValidationError(
            detail="market_code does not match sales channel",
        )
