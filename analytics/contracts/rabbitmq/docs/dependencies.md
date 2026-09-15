# Dependencies

The contract itself is language-neutral.

Validation tooling in this package:
- Python `jsonschema` — development/CI-only schema validation.
- PyYAML — development/CI-only YAML parsing.

These are not Shopware runtime dependencies.

The Shopware implementation must separately document the existing/new PHP AMQP, outbox and worker dependencies and their licenses before merge.
