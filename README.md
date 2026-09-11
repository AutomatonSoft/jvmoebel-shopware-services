# jvmoebel-services

Репозиторий сервисов.

- [AR API](ar/README.md) — работа из каталога `ar/`, команды в [`ar/README.txt`](ar/README.txt)
- [Analytics API](analytics/README.md) — работа из каталога `analytics/`, команды в [`analytics/README.txt`](analytics/README.txt)

Команды из корня — в [`README.txt`](README.txt).

**Deploy.** Workflow `AR Deploy stage` проверяет и выкладывает только AR (`ar/compose.deploy.yml`, артефакт из `ar/`). Analytics в этот pipeline не входит: зелёный AR Deploy не означает, что Analytics задеплоен. Готовность Analytics к выкладке проверяет CI job `Analytics deployment validation` (compose, image, миграции, backend, worker). На сервер Analytics этим workflow не уезжает.

Внутри контейнеров API слушает `8000`, Postgres — `5432`, RabbitMQ — `5672` / `15672`. Production Postgres и RabbitMQ на хост не публикуются: сервисы ходят друг к другу по Docker network.

## Production ports

`.env.example` / `docker-compose.yml`. Наружу только HTTP API.

| Service | HTTP (`PORT`) |
| ------- | ------------- |
| AR | `8000` |
| Analytics | `8002` |

## Dev ports

`.env.dev.example` / `docker-compose.dev.yml`

| Service | HTTP (`PORT_DEV`) | Postgres (`POSTGRES_DEV_EXTERNAL_PORT`) | RabbitMQ AMQP | RabbitMQ management |
| ------- | ----------------- | --------------------------------------- | ------------- | ------------------- |
| AR | `8001` | `5436` | — | — |
| Analytics | `8003` | `5437` | `5673` | `15673` |

## Test ports

`.env.test.example` / `docker-compose.test.yml`. Pytest ходит в Postgres на `localhost`.

| Service | Postgres (`POSTGRES_PORT` / `POSTGRES_EXTERNAL_PORT`) |
| ------- | ----------------------------------------------------- |
| AR | `5439` |
| Analytics | `5440` |




---

# Scope поставки

Analytics в этом репозитории можно разрабатывать и тестировать на фикстурах до появления producers.

## Что реализовано в этом репозитории

- Analytics API (ingest + read)
- HTTP ingestion frontend events
- RabbitMQ consumer подтверждённых Shopware events
- projections, attribution, reports, Customer Journey
- JSON Schema / OpenAPI / AsyncAPI contracts

## Что не входит в этот PR (отдельные задачи, другие репозитории)

В этом PR back, front и docs-репозитории не меняются.

Backend (`jvmoebel-shopware-back`):

- transactional outbox
- RabbitMQ publisher
- стабильный `event_id`
- aggregate versions
- producer retry
- webhook/provider deduplication

Frontend (Next.js):

- отправка frontend events
- visitor/session IDs
- consent
- retry/batching
- безопасная доставка через BFF

Закрытый dashboard UI в этом PR не реализован.

## Критерии готовности второй поставки

- Подтверждённый purchase отправляется в GA4 один раз с устойчивым transaction ID.
- Lead conversions создаются один раз на Lead и разделяются по каналу.
- Sale conversions создаются только из `order_paid` или подтверждённой Manual Sale.
- Повтор исходного события не создаёт вторую Google conversion.
- Consent и доступные рекламные идентификаторы проверяются до отправки.
- Временные ошибки повторяются автоматически, постоянные видны оператору.
- Работает ручной retry.
- В Dashboard видны status, attempts, request ID и последняя безопасная ошибка.
- Недоступность Google не влияет на приём внутренних событий и отчётность.
- Google integrations покрыты mocks и доступными test/sandbox/validate-only modes; после получения реальных доступов выполнены smoke tests.
- Очередь, статусы, retry и диагностика внешних конверсий.
- Conversion operations UI.
- Безопасный enhanced-conversion contract.
- Google corrections для уже принятых внутренних Refunds.
- Read-only summary API для Shopware Lead card.
- Закрытый dashboard: обзор, отчёты, Journey, conversions; loading, empty и error states.
- Необработанные сообщения в `analytics.shopware.events.dlq` наблюдаемы и могут быть повторены оператором.