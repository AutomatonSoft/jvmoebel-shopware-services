#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys

from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[1]
UUID_V4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

STEMS = {
    "session_started": "session-started",
    "product_viewed": "product-viewed",
    "add_to_cart": "add-to-cart",
    "checkout_started": "checkout-started",
    "payment_methods_shown": "payment-methods-shown",
    "payment_method_selected": "payment-method-selected",
    "payment_failed": "payment-failed",
    "contact_intent": "contact-intent",
}

READ_PATHS = (
    "/analytics/overview",
    "/analytics/funnel",
    "/analytics/sources",
    "/analytics/contact-channels",
    "/analytics/products",
    "/analytics/payment-methods",
    "/analytics/period-comparison",
    "/analytics/journey/search",
    "/analytics/visitors/{visitor_id}/journey",
    "/analytics/leads/{lead_id}/journey",
    "/analytics/orders/{order_id}/journey",
    "/analytics/customers/{customer_id}/journey",
)

RESPONSE_EXAMPLES = {
    "overview": "overview",
    "funnel": "funnel",
    "sources": "sources",
    "contact-channels": "contact-channels",
    "products": "products",
    "payment-methods": "payment-methods",
    "period-comparison": "period-comparison",
    "journey": "journey",
    "journey-search": "journey-search",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(example: Path, expected: bool) -> bool:
    doc = load(example)
    event_type = doc.get("event_type")
    stem = STEMS.get(event_type)
    if stem is None:
        if expected:
            print(f"FAIL {example.name}: unknown event_type {event_type!r}")
            return False
        print(f"OK   {example.name}")
        return True
    schema_path = ROOT / "schemas" / "events" / f"{stem}.event.schema.json"
    schema = load(schema_path)
    resolver = RefResolver(
        base_uri=schema_path.resolve().as_uri(),
        referrer=schema,
    )
    validator = Draft202012Validator(
        schema,
        resolver=resolver,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    errors = list(validator.iter_errors(doc))
    actual = len(errors) == 0
    if actual != expected:
        print(f"FAIL {example.name}: expected valid={expected}")
        for err in errors[:10]:
            print("  -", "/".join(str(x) for x in err.absolute_path), err.message)
        return False
    print(f"OK   {example.name}")
    return True


def _validator(schema_path: Path) -> Draft202012Validator:
    schema = load(schema_path)
    resolver = RefResolver(
        base_uri=schema_path.resolve().as_uri(),
        referrer=schema,
    )
    return Draft202012Validator(
        schema,
        resolver=resolver,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def extra_invariants() -> bool:
    ok = True
    openapi = (ROOT / "openapi.yaml").read_text(encoding="utf-8")
    if not openapi.startswith("openapi:"):
        print("FAIL openapi.yaml: missing openapi version line")
        ok = False
    if "./schemas/events/" not in openapi:
        print("FAIL openapi.yaml: must $ref event JSON Schemas")
        ok = False
    if "./schemas/responses/" not in openapi:
        print("FAIL openapi.yaml: must $ref read-API JSON Schemas")
        ok = False
    if "readBearer:" not in openapi:
        print("FAIL openapi.yaml: missing readBearer security scheme")
        ok = False
    for path in READ_PATHS:
        if f"  {path}:" not in openapi:
            print(f"FAIL openapi.yaml: missing path {path}")
            ok = False
    for stem, schema_stem in RESPONSE_EXAMPLES.items():
        example = ROOT / "examples" / "responses" / f"{stem}.json"
        schema_path = ROOT / "schemas" / "responses" / f"{schema_stem}.schema.json"
        if not example.exists():
            print(f"FAIL missing response example {example.name}")
            ok = False
            continue
        errors = list(_validator(schema_path).iter_errors(load(example)))
        if errors:
            print(f"FAIL {example.name}: expected valid response")
            for err in errors[:10]:
                print("  -", "/".join(str(x) for x in err.absolute_path), err.message)
            ok = False
        else:
            print(f"OK   {example.name}")
    for path in (ROOT / "examples" / "valid").glob("*.json"):
        doc = load(path)
        if doc.get("source") != "nextjs":
            print(f"FAIL {path.name}: source must be nextjs")
            ok = False
        if "aggregate_type" in doc or "aggregate_id" in doc:
            print(f"FAIL {path.name}: aggregate_* is forbidden on HTTP events")
            ok = False
        if not UUID_V4.match(str(doc.get("event_id", ""))):
            print(f"FAIL {path.name}: event_id must be UUID v4")
            ok = False
        if doc.get("event_type") not in STEMS:
            print(f"FAIL {path.name}: event_type not in HTTP allowlist")
            ok = False
    return ok


def main() -> None:
    ok = True
    for path in sorted((ROOT / "examples" / "valid").glob("*.json")):
        ok = validate(path, True) and ok
    for path in sorted((ROOT / "examples" / "invalid").glob("*.json")):
        ok = validate(path, False) and ok
    ok = extra_invariants() and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
