# Contract versioning

Canonical JSON Schemas are the source of truth for both HTTP ingest and RabbitMQ events. OpenAPI and AsyncAPI `$ref` those schemas; they must not define independent DTO shapes.

## Events (`event_type` + `event_version`)

HTTP frontend events and Shopware backend events follow the same schema rule: an agreed v1 schema is immutable (`additionalProperties: false`).

Detailed change list: [`rabbitmq/compatibility.md`](rabbitmq/compatibility.md). It applies to `contracts/http/` as well.

Summary:

- Changing an existing envelope/payload (add/remove/rename field, type, required, enum, semantics) requires a new `event_version`.
- Adding a new `event_type` with its own v1 schema does not bump other events.
- Analytics validates the exact schema for `event_type + event_version`. Unknown type or version is rejected; it is not interpreted approximately.
- Shopware and Next.js must not emit a new `event_version` until Analytics accepts it.

## HTTP API (`/api/v1`)

Incompatible changes to ingest or read-API request/response contracts are released as a new API version (`/api/v2`), not as a silent edit of v1.

Compatible additive documentation that does not change validation may stay on v1.

## Coordination

Analytics owns schema design. Shopware confirms it can emit backend events. After agreement the schemas here are the single source of truth.
