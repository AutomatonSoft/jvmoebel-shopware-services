from pathlib import Path

ANALYTICS_ROOT = Path(__file__).resolve().parents[3]
HTTP_CONTRACTS_ROOT = ANALYTICS_ROOT / "contracts" / "http"

HTTP_EVENT_STEMS = {
    "session_started": "session-started",
    "product_viewed": "product-viewed",
    "add_to_cart": "add-to-cart",
    "checkout_started": "checkout-started",
    "payment_methods_shown": "payment-methods-shown",
    "payment_method_selected": "payment-method-selected",
    "payment_failed": "payment-failed",
    "contact_intent": "contact-intent",
}


def http_event_schema_path(event_type: str) -> Path:
    # по типу события из словаря собираем путь к JSON Schema
    stem = HTTP_EVENT_STEMS[event_type]
    return (
        HTTP_CONTRACTS_ROOT
        / "schemas"
        / "events"
        / f"{stem}.event.schema.json"
    )
