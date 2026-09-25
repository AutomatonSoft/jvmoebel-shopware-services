from typing import Any

EVENT_PAYLOAD_IDENTIFYING_KEYS = (
    "click_ids",
    "utm",
    "landing_page",
    "referrer",
    "device",
)

VISITOR_IDENTIFYING_FIELDS = (
    "first_touch_gclid",
    "first_touch_gbraid",
    "first_touch_wbraid",
    "first_touch_utm_source",
    "first_touch_utm_medium",
    "first_touch_utm_campaign",
    "first_touch_utm_content",
    "first_touch_utm_term",
    "first_touch_landing_page",
    "first_touch_referrer",
    "last_non_direct_gclid",
    "last_non_direct_gbraid",
    "last_non_direct_wbraid",
    "last_non_direct_utm_source",
    "last_non_direct_utm_medium",
    "last_non_direct_utm_campaign",
    "last_non_direct_utm_content",
    "last_non_direct_utm_term",
    "last_non_direct_landing_page",
    "last_non_direct_referrer",
)

SESSION_IDENTIFYING_FIELDS = (
    "gclid",
    "gbraid",
    "wbraid",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "landing_page",
    "referrer",
)

TOUCH_IDENTIFYING_FIELDS = SESSION_IDENTIFYING_FIELDS

SNAPSHOT_IDENTIFYING_FIELDS = (
    "attr_first_touch_gclid",
    "attr_first_touch_gbraid",
    "attr_first_touch_wbraid",
    "attr_first_touch_utm_source",
    "attr_first_touch_utm_medium",
    "attr_first_touch_utm_campaign",
    "attr_first_touch_utm_content",
    "attr_first_touch_utm_term",
    "attr_first_touch_landing_page",
    "attr_first_touch_referrer",
    "attr_last_non_direct_gclid",
    "attr_last_non_direct_gbraid",
    "attr_last_non_direct_wbraid",
    "attr_last_non_direct_utm_source",
    "attr_last_non_direct_utm_medium",
    "attr_last_non_direct_utm_campaign",
    "attr_last_non_direct_utm_content",
    "attr_last_non_direct_utm_term",
    "attr_last_non_direct_landing_page",
    "attr_last_non_direct_referrer",
)


def identifying_nulls(fields: tuple[str, ...]) -> dict[str, None]:
    return {field: None for field in fields}


def redact_event_body(body: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(body)
    payload = redacted.get("payload")
    if not isinstance(payload, dict):
        return redacted
    cleaned = dict(payload)
    for key in EVENT_PAYLOAD_IDENTIFYING_KEYS:
        cleaned.pop(key, None)
    redacted["payload"] = cleaned
    return redacted
