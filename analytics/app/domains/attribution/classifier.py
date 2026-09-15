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


def _contains_social(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return any(token in lowered for token in _SOCIAL_TOKENS)


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
    if medium in {"organic", "seo"}:
        return "seo"

    if (
        medium == "social"
        or _contains_social(utm_medium)
        or _contains_social(utm_source)
    ):
        return "social"

    has_click_id = bool(gclid or gbraid or wbraid)
    has_utm = bool(utm_source or utm_medium)
    if referrer and not has_utm and not has_click_id:
        return "referral"

    if not referrer and not has_utm and not has_click_id:
        return "direct"

    return "other"
