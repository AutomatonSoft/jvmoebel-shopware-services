# Compatibility rules — strict v1

The v1 schemas are strict and use `additionalProperties: false`.

Therefore an existing v1 event schema is immutable after agreement.

## Requires a new `event_version`
Any change to an existing event payload/envelope shape requires a new event version, including:
- adding a field, even if it would otherwise be optional;
- removing or renaming a field;
- changing a field type or format;
- changing required/optional status;
- changing enum values or semantics;
- changing the meaning of an existing field;
- changing an event's aggregate/linking semantics.

## Does not require changing existing event versions
- adding a completely new `event_type` with its own schema;
- documentation clarifications that do not alter validation or semantics.

Consumers must validate against the exact schema for `event_type + event_version`.
Shopware must not silently switch versions before Analytics supports the new version.


## v3 note
`contact_received` is a new event type with its own v1 schema. Adding a new event type does not mutate any previously agreed event v1 schema, so existing event versions remain unchanged.
