#!/usr/bin/env python3
from pathlib import Path
import json, sys, yaml
from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[1]

STEMS = {
    "lead_created":"lead-created",
    "contact_received":"contact-received",
    "lead_status_changed":"lead-status-changed",
    "customer_linked":"customer-linked",
    "order_created":"order-created",
    "order_updated":"order-updated",
    "order_paid":"order-paid",
    "order_cancelled":"order-cancelled",
    "manual_sale_created":"manual-sale-created",
    "manual_sale_updated":"manual-sale-updated",
    "manual_sale_cancelled":"manual-sale-cancelled",
    "refund_created":"refund-created",
}

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def validate(example, expected):
    doc = load(example)
    event_type = doc.get("event_type")
    stem = STEMS.get(event_type, "order-paid")
    schema_path = ROOT / "schemas" / "events" / f"{stem}.event.schema.json"
    schema = load(schema_path)
    resolver = RefResolver(base_uri=schema_path.resolve().as_uri(), referrer=schema)
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

def extra_invariants():
    ok = True
    # AsyncAPI and infrastructure files must parse.
    yaml.safe_load((ROOT / "asyncapi.yaml").read_text(encoding="utf-8"))
    topology = yaml.safe_load((ROOT / "infrastructure/rabbitmq-topology.yaml").read_text(encoding="utf-8"))
    if topology["delivery"]["publisher_delivery_mode"] != 2:
        print("FAIL RabbitMQ delivery mode must be persistent (2)")
        ok = False
    if topology["delivery"]["consumer_ack_mode"] != "manual":
        print("FAIL Analytics consumer ACK mode must be manual")
        ok = False

    # aggregate_id equality is an application invariant not expressible as a portable JSON-Schema cross-field equality.
    for p in (ROOT / "examples" / "valid").glob("*.json"):
        d = load(p)
        mapping = {
            "lead": "lead_id",
            "contact": "contact_id",
            "customer": "customer_id",
            "order": "order_id",
            "manual_sale": "manual_sale_id",
            "refund": "refund_id",
        }
        id_field = mapping[d["aggregate_type"]]
        if d.get("aggregate_id") != d.get(id_field):
            print(f"FAIL {p.name}: aggregate_id != {id_field}")
            ok = False
    return ok

def main():
    ok = True
    for p in sorted((ROOT / "examples" / "valid").glob("*.json")):
        ok = validate(p, True) and ok
    for p in sorted((ROOT / "examples" / "invalid").glob("*.json")):
        ok = validate(p, False) and ok
    ok = extra_invariants() and ok
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
