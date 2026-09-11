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


## Первая поставка (Analytics Core)


- Одиночные и пакетные события принимаются и валидируются.
- Повторный `event_id` не создаёт дублей.
- Public HTTP ingestion принимает только разрешённые frontend events и защищён rate/payload/batch limits и проверкой Sales Channel.
- Backend-события Shopware принимаются из RabbitMQ с отдельными credentials/permissions.
- Visitor, Session, Cart, Lead, Customer, Order и Manual Sale связываются по переданным идентификаторам.
- First Touch не перезаписывается, Last Non-Direct Touch рассчитывается по зафиксированным правилам.
- Прямой визит не стирает известный рекламный источник.
- `contact_received` и `lead_created` считаются раздельно.
- `lead_status_changed` в Won не считается продажей.
- Оплата подтверждается только `order_paid`.
- Manual Sale не дублирует Shopware Order.
- `order_updated` корректирует неоплаченный Order без создания Sale conversion.
- Полный и частичный `refund_created` отражается в Journey и корректирует net revenue без изменения исходного gross revenue.
- Рассчитываются overview, ecommerce- и Lead-воронки.
- Доступны отчёты по источникам, каналам обращений, товарам и способам оплаты.
- Реализована возможнось сравнить показатели за 2 периода.
- Реализована возможнось открыть Journey по Visitor, Lead, Order и Customer.
- Отчёты фильтруются по периоду и Sales Channel.
- Денежные показатели разных валют не суммируются без настроенного FX conversion.
- Dashboard обрабатывает loading, empty и error states.
- API описано в OpenAPI с примерами событий.
- Основные сценарии покрыты автоматическими тестами.

Закрытый dashboard UI в этом PR не реализован. Критерий про loading / empty / error закрывается во второй поставке.

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