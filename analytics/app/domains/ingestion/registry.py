from pathlib import Path

ANALYTICS_ROOT = Path(__file__).resolve().parents[3]
HTTP_CONTRACTS_ROOT = ANALYTICS_ROOT / "contracts" / "http"
RABBITMQ_CONTRACTS_ROOT = ANALYTICS_ROOT / "contracts" / "rabbitmq"

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

RABBIT_EVENT_STEMS = {
    "lead_created": "lead-created",
    "contact_received": "contact-received",
    "lead_status_changed": "lead-status-changed",
    "customer_linked": "customer-linked",
    "order_created": "order-created",
    "order_updated": "order-updated",
    "order_paid": "order-paid",
    "order_cancelled": "order-cancelled",
    "manual_sale_created": "manual-sale-created",
    "manual_sale_updated": "manual-sale-updated",
    "manual_sale_cancelled": "manual-sale-cancelled",
    "refund_created": "refund-created",
}


def http_event_schema_path(event_type: str) -> Path:
    # по типу события из словаря собираем путь к JSON Schema
    stem = HTTP_EVENT_STEMS[event_type]
    return HTTP_CONTRACTS_ROOT / "schemas" / "events" / f"{stem}.event.schema.json"


def rabbit_event_schema_path(event_type: str) -> Path:
    stem = RABBIT_EVENT_STEMS[event_type]
    return RABBITMQ_CONTRACTS_ROOT / "schemas" / "events" / f"{stem}.event.schema.json"
