# Migration / rollback requirements

Runtime implementation must provide migrations for:
- Contact entity/storage;
- Lead entity/storage;
- ManualSale entity/storage;
- transactional outbox;
- input-deduplication storage/unique constraints;
- required Lead ↔ Customer and Lead ↔ Order relations.

One Shopware Order may reference at most one originating Lead.
Rollback/forward procedures must not silently discard unpublished outbox rows.
