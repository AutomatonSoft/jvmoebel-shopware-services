# Shopware 6.7 → Analytics Service contract v3

This package is the updated machine-readable SW-001 contract.

## v2 review fixes
- `customer_linked` is customer-centric: requires `visitor_id + customer_id`; `lead_id` is optional.
- `customer` added to aggregate types.
- `cart_id` and `refund_id` added to envelope.
- Currency removed from envelope and lives only in monetary payloads.
- Semantic constraints added for paid/cancelled/new/won/manual-sale-update cases.
- Negative monetary values are invalid.
- `refund_created.line_items` is optional and `refunded_at` is explicit.
- `order_updated.change_reasons` is an array and only pre-paid/non-specialized states are allowed.
- `payment_method` is a stable technical key.
- `product_number` is required only for `item_type=product`.
- RabbitMQ queue/bindings/retry/DLX/DLQ/persistent delivery/manual ACK are defined in `infrastructure/rabbitmq-topology.yaml` and referenced from AsyncAPI.
- Compatibility is strict: adding a field to an existing v1 schema requires a new `event_version`.
- Negative validation examples cover the semantic review cases.

## Validate
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r tests/requirements.txt
python tests/validate_contract.py
```

The validation suite is intended to run locally and in CI on every contract change.


## v3 Contact extension

`Contact` is now an explicit Shopware operational entity.

The contract adds:
- `contact_id` to the common envelope;
- `contact` aggregate type;
- `contact_received` event v1;
- `shopware.contact.received` routing key;
- Contact payload/schema, AsyncAPI message/channel, RabbitMQ binding;
- valid/invalid Contact examples and validation coverage.

`contact_received` is emitted for every confirmed contact. It requires `contact_id` and the linked `lead_id`.
`visitor_id` remains optional because direct email/phone contacts may not have a browser identifier.

Raw contact PII (name, email, phone, message text) stays in Shopware and is not published to Analytics.
