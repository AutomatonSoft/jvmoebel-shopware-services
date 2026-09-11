# Operations

## Transport split
Shopware internal queues remain on Redis.
RabbitMQ is used only for Shopware → Analytics interservice events.

## Transactional outbox
This is a Shopware producer contract. The outbox and RabbitMQ publisher are implemented in `jvmoebel-shopware-back`, not in this Analytics repository.

The Shopware business mutation and outbox insert MUST commit in one DB transaction.
The outbox worker publishes pending records using persistent AMQP messages.
If RabbitMQ is unavailable, the business operation remains committed and the outbox row remains pending.
Re-publication of the same outbox row keeps the same `event_id`.

## Analytics consumption
Analytics consumes `analytics.shopware.events` with manual ACK.
ACK is sent only after successful processing or confirmed `event_id` duplicate
of the same event. An `event_id` collision (same id, different payload / type /
aggregate) is a terminal failure and goes to `analytics.shopware.events.dlq`
without retry.
Transient failures follow bounded retry policy.
Terminal failures go to `analytics.shopware.events.dlq`.

See `../infrastructure/rabbitmq-topology.yaml` for the agreed topology contract.

## Source-request deduplication
Shopware must deduplicate:
- HTTP form submissions by stable `submission_id`;
- provider webhooks by provider + stable event/message id;
- payment callbacks by provider + stable callback/transaction id.

This deduplication happens before creating a second Lead/Order/ManualSale/refund business fact.


## Contact provider flow
Email/WhatsApp/Phone provider webhooks terminate in Shopware.
Shopware verifies/authenticates the provider callback where supported, deduplicates the provider event, persists the Contact and resolves/creates its Lead.
Only after the business fact is persisted does the outbox publish normalized `contact_received`.
Raw PII and raw message content are not placed on RabbitMQ.
