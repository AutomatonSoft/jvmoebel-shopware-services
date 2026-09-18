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


def classify_source(
    *,
    gclid: str | None,
    gbraid: str | None,
    wbraid: str | None,
    utm_source: str | None,
    utm_medium: str | None,
    referrer: str | None,
) -> str:
    if gclid or gbraid or wbraid:
        return "google_ads"

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
