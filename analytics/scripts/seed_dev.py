#!/usr/bin/env python3
"""Send contract fixtures into HTTP ingest + RabbitMQ so the worker fills projections."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import aio_pika
from aio_pika import DeliveryMode, ExchangeType
from dotenv import load_dotenv
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[1]
HTTP_EXAMPLES = ROOT / "contracts" / "http" / "examples" / "valid"
RABBIT_EXAMPLES = ROOT / "contracts" / "rabbitmq" / "examples" / "valid"
ROUTING_KEYS_PATH = ROOT / "contracts" / "rabbitmq" / "routing-keys.json"
EVENTS_EXCHANGE = "shopware.analytics.events"
ORIGIN = "https://www.jvmoebel.de"
HTTP_BATCH_SIZE = 40
CHANNEL_WEB = "018f1a2b3c4d5e6f7890abcdef123456"

BROWSE = ("session-started", "product-viewed")
CART = (*BROWSE, "add-to-cart")
CHECKOUT = (
    *CART,
    "checkout-started",
    "payment-methods-shown",
    "payment-method-selected",
)
INTENT = ("session-started", "contact-intent")
FAILED = (*CHECKOUT, "payment-failed")

PAID = (
    "lead-created",
    "contact-received",
    "customer-linked",
    "order-created",
    "order-paid",
)
LEAD_ONLY = ("lead-created", "contact-received")
LEAD_CONTACTED = (*LEAD_ONLY, "lead-status-changed")
LEAD_STATUS_TWICE = (*LEAD_ONLY, "lead-status-changed", "lead-status-changed")
PHONE = ("lead-created", "contact-received-phone")
DIRECT = ("lead-created", "contact-received-direct-email")
MANUAL = ("lead-created", "manual-sale-created")
MANUAL_CANCEL = (*MANUAL, "manual-sale-cancelled")
PAID_REFUND = (*PAID, "refund-created")
PAID_WON = (*PAID, "lead-status-changed")
PAID_CANCELLED = (
    "lead-created",
    "contact-received",
    "customer-linked",
    "order-created",
    "order-cancelled",
)
ORDER_OPEN = (
    "lead-created",
    "contact-received",
    "customer-linked",
    "order-created",
)

FIXTURE_IDS = (
    "550e8400-e29b-41d4-a716-446655440000",
    "9b1de427-512a-482e-a2bf-66d1f6de06e3",
    "161ac41f-6684-4757-b9ec-47e107f7b04e",
    "8fbf6d3c-7d55-49d2-8442-7be5fcad934e",
    "018f1111111111111111111111111111",
    "018f2222222222222222222222222222",
    "018f3333333333333333333333333333",
    "018f4444444444444444444444444444",
    "018f5555555555555555555555555555",
    "018f6666666666666666666666666666",
    "018f7777777777777777777777777777",
    "018f7777777777777777777777777788",
)

DEVICES = (
    {"device_type": "desktop", "browser": "chrome", "os": "windows"},
    {"device_type": "desktop", "browser": "firefox", "os": "linux"},
    {"device_type": "desktop", "browser": "safari", "os": "macos"},
    {"device_type": "mobile", "browser": "safari", "os": "ios"},
    {"device_type": "mobile", "browser": "chrome", "os": "android"},
    {"device_type": "tablet", "browser": "safari", "os": "ipados"},
    {"device_type": "tablet", "browser": "chrome", "os": "android"},
)
PAYMENTS = (
    "paypal",
    "invoice",
    "installment",
    "creditcard",
    "prepayment",
    "klarna",
)
PAYMENT_ERRORS = (
    ("provider_declined", "INSTRUMENT_DECLINED", "provider"),
    ("timeout", "GATEWAY_TIMEOUT", "redirect"),
    ("3ds_failed", "3DS_CHALLENGE", "provider"),
    ("insufficient_funds", "INSUFFICIENT_FUNDS", "provider"),
    ("validation", "INVALID_CARD", "checkout"),
)
INTENT_ACTIONS = ("click", "open", "submit")
CONTACT_TYPE_BY_CHANNEL = {
    "form": "offer_request",
    "email": "direct_email",
    "whatsapp": "whatsapp_message",
    "phone": "callback_request",
}
REFERRERS = {
    "google": "https://www.google.com/",
    "youtube": "https://www.youtube.com/",
    "facebook": "https://www.facebook.com/",
    "instagram": "https://www.instagram.com/",
    "bing": "https://www.bing.com/",
    "pinterest": "https://www.pinterest.de/",
    "newsletter": "https://mail.jvmoebel.de/campaign",
    "affiliate": "https://www.moebel.de/",
}

Journey = tuple[int, int, tuple[str, ...], tuple[str, ...], dict[str, Any]]


def money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def product(
    sku: str,
    name: str,
    category: str,
    price: str,
    *,
    utm_source: str | None,
    utm_medium: str | None,
    utm_campaign: str | None,
    channel: str,
    currency: str = "EUR",
    quantity: int = 1,
    utm_content: str | None = None,
    utm_term: str | None = None,
    click_id: str | None = None,
) -> dict[str, Any]:
    referrer = REFERRERS.get(utm_source or "", "https://www.jvmoebel.de/")
    if utm_source is None:
        referrer = None
    return {
        "sku": sku,
        "name": name,
        "category": category,
        "price": price,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "utm_content": utm_content,
        "utm_term": utm_term,
        "channel": channel,
        "currency": currency,
        "quantity": quantity,
        "sales_channel_id": CHANNEL_WEB,
        "referrer": referrer,
        "click_id": click_id,
    }


CATALOGS = (
    product(
        "SOFA-001",
        "Sofa Milano",
        "sofas",
        "2499.00",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="sofas-de-2026",
        utm_content="rsa-1",
        utm_term="sofa",
        channel="form",
        click_id="gclid",
    ),
    product(
        "TABLE-002",
        "Esstisch Berlin",
        "tables",
        "890.00",
        utm_source="newsletter",
        utm_medium="email",
        utm_campaign="tables-sep",
        channel="email",
    ),
    product(
        "CHAIR-003",
        "Stuhl Hamburg",
        "chairs",
        "149.00",
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        channel="whatsapp",
    ),
    product(
        "BED-004",
        "Bett Köln",
        "beds",
        "1299.00",
        utm_source="facebook",
        utm_medium="paid_social",
        utm_campaign="beds-retarget",
        channel="form",
        quantity=1,
    ),
    product(
        "LAMP-005",
        "Lampe Leipzig",
        "lighting",
        "89.90",
        utm_source="bing",
        utm_medium="cpc",
        utm_campaign="lighting-brand",
        channel="form",
        quantity=2,
    ),
    product(
        "RUG-006",
        "Teppich München",
        "rugs",
        "349.00",
        utm_source="pinterest",
        utm_medium="social",
        utm_campaign="rugs-inspo",
        channel="form",
    ),
    product(
        "DESK-007",
        "Schreibtisch Düsseldorf",
        "desks",
        "579.00",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="home-office",
        utm_term="schreibtisch",
        channel="form",
        click_id="gbraid",
    ),
    product(
        "WARD-008",
        "Schrank Stuttgart",
        "wardrobes",
        "1890.00",
        utm_source="instagram",
        utm_medium="paid_social",
        utm_campaign="wardrobes-reels",
        channel="whatsapp",
    ),
    product(
        "STOOL-009",
        "Hocker Bremen",
        "chairs",
        "79.00",
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        channel="form",
        quantity=4,
    ),
    product(
        "MIRROR-010",
        "Spiegel Frankfurt",
        "mirrors",
        "229.00",
        utm_source="affiliate",
        utm_medium="referral",
        utm_campaign="moebel-de",
        channel="email",
    ),
    product(
        "SHELF-011",
        "Regal Hannover",
        "storage",
        "459.00",
        utm_source="youtube",
        utm_medium="video",
        utm_campaign="storage-howto",
        channel="form",
        click_id="wbraid",
    ),
    product(
        "OUT-012",
        "Gartenlounge Kiel",
        "outdoor",
        "1599.00",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="outdoor-summer",
        channel="phone",
        click_id="gclid",
        currency="EUR",
    ),
    product(
        "SOFA-US-013",
        "Sofa Austin",
        "sofas",
        "1899.00",
        utm_source="google",
        utm_medium="cpc",
        utm_campaign="sofas-us",
        channel="form",
        currency="USD",
        click_id="gclid",
    ),
    product(
        "CHAIR-014",
        "Stuhl Dresden",
        "chairs",
        "199.00",
        utm_source="facebook",
        utm_medium="organic_social",
        utm_campaign="chairs-ugc",
        channel="whatsapp",
    ),
)

TEMPLATES: tuple[
    tuple[tuple[str, ...], tuple[str, ...], dict[str, Any]], ...
] = (
    (CHECKOUT, PAID, {}),
    (CHECKOUT, PAID_REFUND, {}),
    (CHECKOUT, PAID_REFUND, {"refund_full": True}),
    (CHECKOUT, PAID_WON, {"lead_path": ("won",)}),
    (CHECKOUT, PAID_CANCELLED, {}),
    (CHECKOUT, ORDER_OPEN, {}),
    (FAILED, (), {}),
    (CART, (), {}),
    (BROWSE, (), {}),
    (BROWSE, (), {}),
    (INTENT, LEAD_ONLY, {}),
    (INTENT, PHONE, {"channel": "phone", "call_duration": 240}),
    (INTENT, PHONE, {"channel": "phone", "call_duration": 0, "connection_status": "not_answered"}),
    (INTENT, PHONE, {"channel": "phone", "call_duration": 12, "connection_status": "busy"}),
    (INTENT, MANUAL, {}),
    (INTENT, MANUAL_CANCEL, {}),
    (INTENT, DIRECT, {"channel": "email"}),
    (INTENT, LEAD_CONTACTED, {"lead_path": ("contacted",)}),
    (INTENT, LEAD_STATUS_TWICE, {"lead_path": ("contacted", "offer_sent")}),
    (INTENT, LEAD_STATUS_TWICE, {"lead_path": ("contacted", "lost")}),
    (CART, LEAD_ONLY, {}),
    (CHECKOUT, PAID, {}),
    (FAILED, PHONE, {"channel": "phone", "call_duration": 95}),
    (INTENT, LEAD_ONLY, {"channel": "form", "lead_contact_type": "contact_form"}),
    (INTENT, LEAD_ONLY, {"channel": "form", "lead_contact_type": "callback_request"}),
)


def load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SystemExit(f"{path.name} is not a JSON object")
    return loaded


def remap(value: object, mapping: dict[str, str]) -> object:
    if isinstance(value, dict):
        return {key: remap(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [remap(item, mapping) for item in value]
    if isinstance(value, str) and value in mapping:
        return mapping[value]
    return value


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is missing. Copy .env.dev.example to .env.dev")
    return value


def publisher_url() -> str:
    user = quote(require_env("RABBITMQ_PUBLISHER_USER"), safe="")
    password = quote(require_env("RABBITMQ_PUBLISHER_PASSWORD"), safe="")
    port = os.getenv("RABBITMQ_DEV_EXTERNAL_PORT", "5673")
    return f"amqp://{user}:{password}@127.0.0.1:{port}/shopware-analytics"


def line_total(catalog: dict[str, Any]) -> str:
    unit = Decimal(catalog["price"])
    quantity = int(catalog.get("quantity") or 1)
    return money(unit * quantity)


def set_click_ids(payload: dict[str, Any], catalog: dict[str, Any], tag: str) -> None:
    if catalog["utm_source"] is None:
        payload.pop("click_ids", None)
        return
    kind = catalog.get("click_id")
    if kind not in {"gclid", "gbraid", "wbraid"}:
        payload.pop("click_ids", None)
        return
    payload["click_ids"] = {kind: f"seed-{tag}"}


def apply_utm(payload: dict[str, Any], catalog: dict[str, Any], tag: str) -> None:
    if "utm" not in payload and "click_ids" not in payload and "referrer" not in payload:
        return
    if catalog["utm_source"] is None:
        payload.pop("utm", None)
        payload.pop("click_ids", None)
        if catalog.get("referrer"):
            payload["referrer"] = catalog["referrer"]
        else:
            payload.pop("referrer", None)
        return
    utm = {
        "utm_source": catalog["utm_source"],
        "utm_medium": catalog["utm_medium"],
        "utm_campaign": catalog["utm_campaign"],
    }
    if catalog.get("utm_content"):
        utm["utm_content"] = catalog["utm_content"]
    if catalog.get("utm_term"):
        utm["utm_term"] = catalog["utm_term"]
    payload["utm"] = utm
    set_click_ids(payload, catalog, tag)
    if catalog.get("referrer"):
        payload["referrer"] = catalog["referrer"]


def apply_contact_received(payload: dict[str, Any], catalog: dict[str, Any]) -> None:
    if payload.get("contact_channel") == "phone" or catalog["channel"] == "phone":
        payload["contact_channel"] = "phone"
        payload["contact_type"] = "qualified_call"
        payload["duration_seconds"] = int(catalog.get("call_duration") or 185)
        payload["connection_status"] = catalog.get("connection_status") or "answered"
        return
    if payload.get("contact_type") == "direct_email":
        payload["contact_channel"] = "email"
        payload.pop("duration_seconds", None)
        payload.pop("connection_status", None)
        return
    payload["contact_channel"] = catalog["channel"]
    payload["contact_type"] = catalog.get("lead_contact_type") or CONTACT_TYPE_BY_CHANNEL[
        catalog["channel"]
    ]
    payload.pop("duration_seconds", None)
    payload.pop("connection_status", None)


def apply_catalog(event: dict[str, Any], catalog: dict[str, Any], tag: str) -> None:
    event["sales_channel_id"] = catalog.get("sales_channel_id", CHANNEL_WEB)
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return
    sku = catalog["sku"]
    name = catalog["name"]
    unit_price = catalog["price"]
    quantity = int(catalog.get("quantity") or 1)
    total = line_total(catalog)
    currency = catalog.get("currency") or "EUR"
    if "currency" in payload:
        payload["currency"] = currency
    if "sku" in payload:
        payload["sku"] = sku
        payload["name"] = name
        if "category" in payload:
            payload["category"] = catalog["category"]
        if "quantity" in payload:
            payload["quantity"] = quantity
        if "unit_price" in payload:
            payload["unit_price"] = unit_price
        if "total_price" in payload:
            payload["total_price"] = total
        if "total_amount" in payload:
            payload["total_amount"] = total
    if "product_number" in payload:
        payload["product_number"] = sku
    if "landing_page" in payload:
        slug = sku.lower()
        payload["landing_page"] = f"https://www.jvmoebel.de/{catalog['category']}/{slug}"
    if "device" in payload and catalog.get("device"):
        payload["device"] = catalog["device"]
    if "channel" in payload:
        payload["channel"] = catalog["channel"]
    if "action" in payload and catalog.get("intent_action"):
        payload["action"] = catalog["intent_action"]
    if "contact_channel" in payload and event.get("event_type") == "lead_created":
        payload["contact_channel"] = catalog["channel"]
        payload["contact_type"] = catalog.get("lead_contact_type") or CONTACT_TYPE_BY_CHANNEL[
            catalog["channel"]
        ]
    if event.get("event_type") == "contact_received":
        apply_contact_received(payload, catalog)
    apply_utm(payload, catalog, tag)
    if "methods" in payload:
        selected = catalog.get("payment_method") or "paypal"
        extras = [item for item in PAYMENTS if item != selected]
        payload["methods"] = [selected, *extras[:2]]
    if "payment_method" in payload and event.get("event_type") != "refund_created":
        payload["payment_method"] = catalog.get("payment_method") or payload["payment_method"]
    if "error_category" in payload:
        category, code, stage = catalog.get("payment_error") or PAYMENT_ERRORS[0]
        payload["error_category"] = category
        payload["error_code"] = code
        payload["stage"] = stage
    if "line_items" in payload:
        for item in payload["line_items"]:
            if not isinstance(item, dict):
                continue
            if "sku" in item:
                item["sku"] = sku
                item["name"] = name
            if "product_number" in item:
                item["product_number"] = sku
            if "quantity" in item:
                item["quantity"] = quantity
            if "unit_price" in item:
                item["unit_price"] = unit_price
            if "total_price" in item:
                item["total_price"] = total
            if "currency" in item:
                item["currency"] = currency
        if "total_amount" in payload:
            payload["total_amount"] = total
    if "amount" in payload:
        payload["amount"] = total
        payload["reference"] = f"MS-{tag}"
    if "order_number" in payload:
        payload["order_number"] = f"DEV-{tag}"
    if "refund_amount" in payload:
        if catalog.get("refund_full"):
            payload["refund_amount"] = total
            payload["refund_type"] = "full"
            payload["payment_state"] = "refunded"
        else:
            payload["refund_amount"] = money(Decimal(total) * Decimal("0.12"))
            payload["refund_type"] = "partial"
            payload["payment_state"] = "refunded_partially"
        payload["payment_method"] = catalog.get("payment_method") or "paypal"


def stamp_aggregate_versions(events: list[dict[str, Any]]) -> None:
    versions: dict[str, int] = {}
    for event in events:
        key = event.get("aggregate_type")
        if not isinstance(key, str):
            continue
        versions[key] = versions.get(key, 0) + 1
        event["aggregate_version"] = versions[key]


def apply_lead_path(events: list[dict[str, Any]], catalog: dict[str, Any]) -> None:
    path = catalog.get("lead_path")
    if not path:
        return
    status_events = [
        event for event in events if event.get("event_type") == "lead_status_changed"
    ]
    if len(status_events) != len(path):
        raise SystemExit(
            f"lead_path {path!r} does not match {len(status_events)} status events"
        )
    order_id = next(
        (event.get("order_id") for event in events if event.get("order_id")),
        None,
    )
    manual_sale_id = next(
        (event.get("manual_sale_id") for event in events if event.get("manual_sale_id")),
        None,
    )
    previous = "new"
    for event, new_status in zip(status_events, path, strict=True):
        payload = event["payload"]
        payload["previous_status"] = previous
        payload["new_status"] = new_status
        if new_status == "won":
            if order_id:
                event["order_id"] = order_id
            elif manual_sale_id:
                event["manual_sale_id"] = manual_sale_id
            else:
                raise SystemExit("won lead_status_changed requires order_id or manual_sale_id")
        previous = new_status


def prepare_event(
    stem: str,
    examples: Path,
    mapping: dict[str, str],
    occurred_at: datetime,
    catalog: dict[str, Any],
    tag: str,
) -> dict[str, Any]:
    event = remap(load_json(examples / f"{stem}.json"), mapping)
    if not isinstance(event, dict):
        raise SystemExit(f"{stem} remapped to a non-object")
    stamp = occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    event["event_id"] = str(uuid4())
    event["occurred_at"] = stamp
    consent = event.get("consent")
    if isinstance(consent, dict) and "captured_at" in consent:
        consent["captured_at"] = (occurred_at - timedelta(minutes=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    payload = event.get("payload")
    if isinstance(payload, dict) and "refunded_at" in payload:
        payload["refunded_at"] = stamp
    if isinstance(payload, dict) and "confirmed_at" in payload:
        payload["confirmed_at"] = stamp
    if isinstance(payload, dict) and "cancelled_at" in payload:
        payload["cancelled_at"] = stamp
    apply_catalog(event, catalog, tag)
    return event


def id_mapping() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for fixture_id in FIXTURE_IDS:
        if "-" in fixture_id:
            mapping[fixture_id] = str(uuid4())
        else:
            mapping[fixture_id] = uuid4().hex
    return mapping


def slots_for_day(days_ago: int) -> int:
    if days_ago <= 6:
        return 6
    if days_ago <= 13:
        return 3
    return 2


def journey_specs() -> list[Journey]:
    specs: list[Journey] = []
    hours = (8, 9, 11, 12, 14, 16, 18, 20, 21)
    index = 0
    for days_ago in range(0, 28):
        for slot in range(slots_for_day(days_ago)):
            http_stems, rabbit_stems, extra = TEMPLATES[index % len(TEMPLATES)]
            catalog = {
                **CATALOGS[index % len(CATALOGS)],
                **extra,
                "device": DEVICES[index % len(DEVICES)],
                "payment_method": PAYMENTS[index % len(PAYMENTS)],
                "payment_error": PAYMENT_ERRORS[index % len(PAYMENT_ERRORS)],
                "intent_action": INTENT_ACTIONS[index % len(INTENT_ACTIONS)],
            }
            hour = hours[(days_ago + slot) % len(hours)]
            specs.append((days_ago, hour, http_stems, rabbit_stems, catalog))
            index += 1
    return specs


def build_journeys(
    now: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[Journey]]:
    http_events: list[dict[str, Any]] = []
    rabbit_events: list[dict[str, Any]] = []
    visitor_ids: list[str] = []
    specs = journey_specs()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for index, (days_ago, hour, http_stems, rabbit_stems, catalog) in enumerate(specs):
        mapping = id_mapping()
        visitor_ids.append(mapping["550e8400-e29b-41d4-a716-446655440000"])
        start = (
            today
            - timedelta(days=days_ago)
            + timedelta(hours=hour, minutes=index % 45)
        )
        tag = f"{days_ago:02d}-{index:03d}"
        for offset, stem in enumerate(http_stems):
            http_events.append(
                prepare_event(
                    stem,
                    HTTP_EXAMPLES,
                    mapping,
                    start + timedelta(minutes=offset),
                    catalog,
                    tag,
                )
            )
        rabbit_batch: list[dict[str, Any]] = []
        rabbit_base = start + timedelta(minutes=len(http_stems) + 5)
        for offset, stem in enumerate(rabbit_stems):
            rabbit_batch.append(
                prepare_event(
                    stem,
                    RABBIT_EXAMPLES,
                    mapping,
                    rabbit_base + timedelta(minutes=offset * 3),
                    catalog,
                    tag,
                )
            )
        stamp_aggregate_versions(rabbit_batch)
        apply_lead_path(rabbit_batch, catalog)
        rabbit_events.extend(rabbit_batch)
    return http_events, rabbit_events, visitor_ids, specs


async def publish_http(events: list[dict[str, Any]]) -> None:
    port = os.getenv("PORT_DEV", "8003")
    url = f"http://127.0.0.1:{port}/api/v1/events/batch"
    headers = {
        "Authorization": f"Bearer {require_env('ANALYTICS_INGEST_API_KEY')}",
        "Origin": ORIGIN,
        "Content-Type": "application/json",
    }
    async with AsyncClient(timeout=30) as client:
        for start in range(0, len(events), HTTP_BATCH_SIZE):
            chunk = events[start : start + HTTP_BATCH_SIZE]
            response = await client.post(url, headers=headers, json={"events": chunk})
            if response.status_code != 200:
                raise SystemExit(
                    f"HTTP ingest failed {response.status_code}: {response.text}"
                )
            rejected = [
                item
                for item in response.json().get("results", [])
                if item.get("status") == "rejected"
            ]
            if rejected:
                raise SystemExit(f"HTTP ingest rejected events: {rejected}")
    print(f"HTTP ingest: {len(events)} events -> {url}")


async def publish_rabbit(events: list[dict[str, Any]]) -> None:
    routing = load_json(ROUTING_KEYS_PATH)["routing_keys"]
    connection = await aio_pika.connect_robust(publisher_url())
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            EVENTS_EXCHANGE,
            ExchangeType.TOPIC,
            durable=True,
        )
        for event in events:
            event_type = event["event_type"]
            routing_key = routing[event_type]
            message = aio_pika.Message(
                json.dumps(event).encode("utf-8"),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                message_id=event["event_id"],
            )
            await exchange.publish(message, routing_key=routing_key)
    print(f"Rabbit: {len(events)} events -> {EVENTS_EXCHANGE}")


async def main() -> None:
    env_path = ROOT / ".env.dev"
    if not env_path.exists():
        raise SystemExit("analytics/.env.dev is missing. Copy .env.dev.example")
    load_dotenv(env_path, override=False)
    os.chdir(ROOT)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    http_events, rabbit_events, visitor_ids, specs = build_journeys(now)
    await publish_http(http_events)
    await publish_rabbit(rabbit_events)
    days = sorted({row[0] for row in specs})
    print(
        f"journeys={len(specs)} http={len(http_events)} "
        f"rabbit={len(rabbit_events)} days_ago={days[0]}..{days[-1]}"
    )
    print(f"visitor_id={visitor_ids[0]}")
    print("Wait ~5s for the worker, then open http://127.0.0.1:8003/dashboard")
    print("Default 7d window hides days_ago>=8 — widen period_from to see them.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
