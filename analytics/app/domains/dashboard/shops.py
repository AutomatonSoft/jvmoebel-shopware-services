from urllib.parse import urlsplit

from pydantic import BaseModel

from core.config import settings


class ShopOption(BaseModel):
    id: str
    label: str


class DashboardConfig(BaseModel):
    shops: list[ShopOption]


def _shop_label(origins: list[str], fallback: str) -> str:
    for origin in origins:
        host = urlsplit(origin).hostname
        if host is None:
            continue
        host = host.lower().removeprefix("www.")
        if host in {"test", "localhost"}:
            continue
        return host
    return fallback


def dashboard_config() -> DashboardConfig:
    shops = [
        ShopOption(id=channel.id, label=_shop_label(channel.origins, channel.id))
        for channel in settings.sales_channels
    ]
    return DashboardConfig(shops=shops)
