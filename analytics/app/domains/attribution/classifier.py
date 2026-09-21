from collections.abc import Collection
from urllib.parse import urlsplit

_SOCIAL_TOKENS = (
    "social",
    "facebook",
    "instagram",
    "tiktok",
    "pinterest",
    "linkedin",
    "twitter",
    "youtube",
    "whatsapp",
    "telegram",
)
_PAID_MEDIUMS = {
    "cpc",
    "ppc",
    "paid",
    "display",
    "cpm",
    "cpa",
    "cpl",
    "paid-search",
    "paid_search",
    "shopping",
}
_EMAIL_MEDIUMS = {"email", "e-mail", "newsletter", "mail"}
_REFERRAL_MEDIUMS = {"referral", "affiliate"}
_GOOGLE_SOURCES = {"google", "googleads", "google_ads", "adwords"}
_SEARCH_HOSTS = {
    "bing.com",
    "duckduckgo.com",
    "baidu.com",
    "ecosia.org",
    "yahoo.com",
    "yandex.ru",
    "yandex.com",
}
_SKIP_ORIGIN_HOSTS = {"test", "localhost"}
DEFAULT_REFERRAL_EXCLUSION_HOSTS = frozenset(
    {
        "paypal.com",
        "paypal.me",
        "paypalobjects.com",
        "klarna.com",
        "klarnacdn.net",
        "klarnapayments.com",
        "stripe.com",
        "adyen.com",
        "payone.com",
        "payone.de",
        "sofort.com",
        "giropay.de",
        "amazonpay.com",
        "payments-amazon.com",
        "verifiedbyvisa.com",
        "securecode.com",
        "paypal",
        "klarna",
        "stripe",
        "3dsecure",
        "3d-secure",
        "verifiedbyvisa",
        "securecode",
        "acs",
    }
)


def _contains_social(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return any(token in lowered for token in _SOCIAL_TOKENS)


def _hostname(referrer: str | None) -> str:
    if not referrer:
        return ""
    host = urlsplit(referrer).hostname
    if host is None:
        return ""
    return host.lower().removeprefix("www.")


def _is_search_referrer(referrer: str | None) -> bool:
    host = _hostname(referrer)
    if not host:
        return False
    if host in _SEARCH_HOSTS:
        return True
    if host.endswith(".bing.com") or host.endswith(".yahoo.com"):
        return True
    return host.split(".", 1)[0] == "google"


def _is_google_source(utm_source: str | None) -> bool:
    value = (utm_source or "").lower()
    return value in _GOOGLE_SOURCES or value.startswith("google_")


def _is_ipv4(host: str) -> bool:
    parts = host.split(".")
    return len(parts) == 4 and all(part.isdigit() for part in parts)


def _normalize_exclusion_rule(value: str) -> str:
    stripped = value.strip().lower()
    if not stripped:
        return ""
    if "://" in stripped:
        return _hostname(stripped)
    return stripped.removeprefix("www.")


def _is_excluded_host(host: str, excluded: Collection[str]) -> bool:
    if not host:
        return False
    labels = host.split(".")
    for rule in excluded:
        if not rule:
            continue
        if rule == "acs":
            if host.startswith("acs.") and host.count(".") >= 2:
                return True
            continue
        if "." in rule:
            if host == rule or host.endswith("." + rule):
                return True
            continue
        if rule in labels:
            return True
    return False


def collect_referral_exclusion_hosts(
    *,
    extra: Collection[str] = (),
    origin_urls: Collection[str] = (),
) -> frozenset[str]:
    hosts = set(DEFAULT_REFERRAL_EXCLUSION_HOSTS)
    for item in extra:
        rule = _normalize_exclusion_rule(item)
        if rule:
            hosts.add(rule)
    for origin in origin_urls:
        host = _hostname(origin)
        if not host or host in _SKIP_ORIGIN_HOSTS or _is_ipv4(host):
            continue
        hosts.add(host)
    return frozenset(hosts)


def referral_exclusion_hosts() -> frozenset[str]:
    from core.config import settings

    return collect_referral_exclusion_hosts(
        extra=settings.referral_exclusion_hosts,
        origin_urls=[
            origin
            for channel in settings.sales_channels
            for origin in channel.origins
        ],
    )


def classify_source(
    *,
    gclid: str | None,
    gbraid: str | None,
    wbraid: str | None,
    utm_source: str | None,
    utm_medium: str | None,
    referrer: str | None,
    excluded_hosts: Collection[str] = (),
) -> str:
    if gclid or gbraid or wbraid:
        return "google_ads"

    if _is_excluded_host(_hostname(referrer), excluded_hosts):
        referrer = None

    medium = (utm_medium or "").lower()
    has_utm = bool(utm_source or utm_medium)

    if _is_google_source(utm_source) and medium in _PAID_MEDIUMS:
        return "google_ads"

    if medium in {"organic", "seo"}:
        return "seo"
    if not has_utm and _is_search_referrer(referrer):
        return "seo"

    if (
        medium == "social"
        or _contains_social(utm_medium)
        or _contains_social(utm_source)
    ):
        return "social"

    if medium in _EMAIL_MEDIUMS:
        return "email"

    if medium in _PAID_MEDIUMS:
        return "paid"

    if medium in _REFERRAL_MEDIUMS:
        return "referral"

    if referrer and not has_utm:
        return "referral"

    if not referrer and not has_utm:
        return "direct"

    return "other"
