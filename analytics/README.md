# Analytics API

Analytics API принимает frontend-события Next.js по HTTP, подтверждённые backend-события Shopware из RabbitMQ и отдаёт отчёты и Customer Journey.

HTTP ingest — server-to-server. Браузер не вызывает Analytics и не получает `ANALYTICS_INGEST_API_KEY`.

```text
Browser (без секрета)
  → Next.js server / Route Handler / BFF
  → POST /api/v1/events
```

Ключ живёт только в env Next.js-сервера. Прокси, visitor/session IDs, consent и retry/batching на стороне витрины — отдельная задача, в этом репозитории их нет.

HTTP Base URL:

```text
/api/v1
```

Host port по умолчанию — `8002` (`PORT` в `.env.example`). Внутри контейнера API слушает `8000`.

**Deploy.** `AR Deploy stage` покрывает только AR и не выкладывает Analytics. CI job `Analytics deployment validation` собирает production `docker-compose.yml`, применяет миграции и стартует backend/worker; это проверка, что стек поднимается, а не деплой на Server5.

HTTP ingestion принимает только frontend event types:

```text
session_started
product_viewed
add_to_cart
checkout_started
payment_methods_shown
payment_method_selected
payment_failed
contact_intent
```

Shopware-события (`order_paid`, `lead_created`, `refund_created` и остальные) на публичный HTTP ingest не принимаются. Они приходят в RabbitMQ и описаны в `contracts/rabbitmq/asyncapi.yaml`.

Канонические JSON Schema, OpenAPI и примеры событий лежат в `contracts/http/`.

В общие события нельзя передавать открытые имя, email, телефон, адрес и текст сообщений.

---

## Limits

По умолчанию:

| Setting | Default | Description |
| ------- | ------- | ----------- |
| `MAX_BODY_SIZE` | `262144` (256 KB) | Максимальный размер HTTP request body |
| `MAX_EVENT_PAYLOAD_BYTES` | `32768` (32 KB) | Максимальный размер одного event JSON |
| `MAX_BATCH_EVENTS` | `100` | Максимум событий в `POST /events/batch` |
| `INGEST_RATE_LIMIT` | `600` | Лимит HTTP ingest-запросов на allowlisted Origin или IP за окно |
| `INGEST_RATE_LIMIT_WINDOW_SECONDS` | `60` | Окно rate limit в секундах |
| `INGEST_RATE_LIMIT_MAX_KEYS` | `1024` | Максимум источников запросов |

```env
MAX_BODY_SIZE=262144
MAX_EVENT_PAYLOAD_BYTES=32768
MAX_BATCH_EVENTS=100
INGEST_RATE_LIMIT=600
INGEST_RATE_LIMIT_WINDOW_SECONDS=60
INGEST_RATE_LIMIT_MAX_KEYS=1024
```

Если значения не заданы, используются значения по умолчанию из `app/core/config.py`.

Rate limit хранится in-process и не общий между uvicorn workers и репликами. Redis в этой поставке не используется. Bearer проверяется до записи в store. Ключи с истекшим окном удаляются; при переполнении `INGEST_RATE_LIMIT_MAX_KEYS` новый бакет не создаётся. Origin из allowlist `SALES_CHANNELS` получает свой бакет, неизвестный Origin считается по IP.

`sales_channel_id` проверяется по allowlist `SALES_CHANNELS`. Next.js BFF передаёт Origin/Referer витрины; Origin и `payload`/`domain` должны соответствовать origins этого канала.

---

# Authentication

Ingest и read используют разные Bearer API keys.

```text
POST /api/v1/events
POST /api/v1/events/batch
```

```http
Authorization: Bearer <ANALYTICS_INGEST_API_KEY>
```

```text
GET /api/v1/analytics/*
```

```http
Authorization: Bearer <ANALYTICS_READ_API_KEY>
```

Ключи хранятся в environment variables:

```env
ANALYTICS_INGEST_API_KEY=your-ingest-secret-token
ANALYTICS_READ_API_KEY=your-read-secret-token
```

При отсутствии credentials или неверном token API возвращает:

```http
401 Unauthorized
```

Возможные authentication errors:

```text
Authentication required
```

```text
Invalid authentication scheme
```

```text
Invalid authentication token
```

Ingest key не подходит для read API и наоборот.

`ANALYTICS_INGEST_API_KEY` нельзя класть в browser JS, `NEXT_PUBLIC_*` или GTM. Его держит только Next.js BFF. Примеры `curl` ниже — серверные вызовы, не код витрины.

---

# POST /api/v1/events

Принять одно frontend-событие от Next.js BFF.

Требуется ingest Bearer token. BFF передаёт `Origin` (или `Referer`) витрины из allowlist sales channel.

Повтор с тем же `event_id` не меняет метрики и Journey. API возвращает успешный идемпотентный результат.

### Example

Серверный вызов (BFF или curl с сервера), не из браузера.

```bash
curl -X POST \
  http://localhost:8002/api/v1/events \
  -H "Authorization: Bearer $ANALYTICS_INGEST_API_KEY" \
  -H "Origin: https://www.jvmoebel.de" \
  -H "Content-Type: application/json" \
  -d @contracts/http/examples/valid/session-started.json
```

Пример тела `session_started`:

```json
{
  "event_id": "2f1c3a50-fd24-4f2d-8dd4-42e82b5e9101",
  "event_type": "session_started",
  "event_version": 1,
  "occurred_at": "2026-08-24T09:00:00Z",
  "source": "nextjs",
  "sales_channel_id": "018f1a2b3c4d5e6f7890abcdef123456",
  "market_code": "de",
  "domain": "www.jvmoebel.de",
  "language": "de-DE",
  "visitor_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "9b1de427-512a-482e-a2bf-66d1f6de06e3",
  "consent": {
    "analytics": true,
    "ads": true,
    "captured_at": "2026-08-24T08:59:00Z"
  },
  "payload": {
    "landing_page": "https://www.jvmoebel.de/sofas/sofa-001",
    "referrer": "https://www.google.com/",
    "utm": {
      "utm_source": "google",
      "utm_medium": "cpc",
      "utm_campaign": "sofas-de-2026",
      "utm_content": "rsa-1",
      "utm_term": "sofa"
    },
    "click_ids": {
      "gclid": "Cj0KCQjw-example"
    },
    "device": {
      "device_type": "desktop",
      "browser": "chrome",
      "os": "macos"
    }
  }
}
```

Остальные валидные примеры: `contracts/http/examples/valid/`.

### Response: accepted

```http
HTTP/1.1 200 OK
```

```json
{
  "status": "accepted"
}
```

### Response: duplicate

Повтор **того же** события (тот же `event_id` и те же immutable-поля):

```http
HTTP/1.1 200 OK
```

```json
{
  "status": "duplicate"
}
```

### Response: collision

Тот же `event_id`, но другое событие (`payload`, `event_type`, агрегат или id-поля):

```http
HTTP/1.1 409 Conflict
```

```json
{
  "detail": "event_id collision: payload does not match stored event"
}
```

Журнал не перезаписывается.

### Errors

| Status | Description |
| ------ | ----------- |
| `401` | Missing or invalid ingest API key |
| `409` | Same `event_id` already stored with a different event |
| `413` | HTTP request body exceeds `MAX_BODY_SIZE` |
| `422` | Schema, allowlist, origin/domain or unknown `sales_channel_id` |
| `429` | HTTP ingest rate limit exceeded. `Retry-After` в секундах |

Shopware `event_type` на этом endpoint даёт `422`, даже если payload валиден для RabbitMQ.

---

# POST /api/v1/events/batch

Принять пакет frontend-событий от Next.js BFF.

Требуется ingest Bearer token. BFF передаёт `Origin` (или `Referer`) витрины.

Ошибка одного элемента не скрывает результат остальных. Повтор того же события внутри batch — `duplicate`. Collision (`event_id` уже занят другим событием) возвращает `409` на весь запрос; уже принятые элементы остаются в журнале.

### Request

```json
{
  "events": [
    { "event_id": "...", "event_type": "session_started" }
  ]
}
```

`events` — непустой массив, не длиннее `MAX_BATCH_EVENTS`.

### Example

Серверный вызов (BFF или curl с сервера), не из браузера.

```bash
curl -X POST \
  http://localhost:8002/api/v1/events/batch \
  -H "Authorization: Bearer $ANALYTICS_INGEST_API_KEY" \
  -H "Origin: https://www.jvmoebel.de" \
  -H "Content-Type: application/json" \
  -d "{\"events\":[$(cat contracts/http/examples/valid/session-started.json)]}"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "results": [
    {
      "index": 0,
      "event_id": "2f1c3a50-fd24-4f2d-8dd4-42e82b5e9101",
      "status": "accepted"
    },
    {
      "index": 1,
      "event_id": "2f1c3a50-fd24-4f2d-8dd4-42e82b5e9101",
      "status": "duplicate"
    },
    {
      "index": 2,
      "event_id": null,
      "status": "rejected",
      "detail": "Event type is not allowed for HTTP ingestion"
    }
  ]
}
```

`status` элемента:

```text
accepted
duplicate
rejected
```

Невалидный envelope всего batch (`events` отсутствует, пустой или слишком большой) возвращает `422`. Отклонение одного события внутри валидного batch остаётся в `200` со `status: rejected`.

### Errors

| Status | Description |
| ------ | ----------- |
| `401` | Missing or invalid ingest API key |
| `409` | Same `event_id` already stored with a different event |
| `413` | HTTP request body exceeds `MAX_BODY_SIZE` |
| `422` | Invalid batch envelope, schema, allowlist, origin/domain or unknown `sales_channel_id` |
| `429` | HTTP ingest rate limit exceeded. `Retry-After` в секундах |

---

# Report filters

Все `GET /api/v1/analytics/*` отчёты, кроме Journey, принимают query-параметры:

| Parameter | Required | Description |
| --------- | -------- | ----------- |
| `period_from` | yes | Начало периода, `date-time` |
| `period_to` | yes | Конец периода, `date-time` |
| `sales_channel` | no | Shopware sales channel ID, 32 hex |
| `market` | no | `de`, `at`, `ch`, `uk`, `it`, `pl` |
| `source` | no | Источник атрибуции, например `google_ads` |
| `campaign` | no | Campaign |
| `sku` | no | SKU |
| `channel` | no | `form`, `email`, `whatsapp`, `phone` |
| `payment_method` | no | Технический ключ способа оплаты |
| `currency` | no | ISO 4217, 3 символа |
| `attribution_model` | no | `first_touch` или `last_non_direct`. По умолчанию `last_non_direct` |

`period-comparison` дополнительно требует:

| Parameter | Required | Description |
| --------- | -------- | ----------- |
| `compare_from` | yes | Начало сравниваемого периода |
| `compare_to` | yes | Конец сравниваемого периода |

Денежные показатели разных валют не суммируются. `money` — массив breakdown по `currency`.

Неизвестный `sales_channel` не даёт `422`: отчёт возвращает `200` с нулями.

Требуется read Bearer token.

---

# GET /api/v1/analytics/overview

Основные показатели периода: visitors, sessions, воронка-счётчики, leads, orders, manual sales, money, конверсии и время до Lead/Sale.

### Example

```bash
curl "http://localhost:8002/api/v1/analytics/overview?period_from=2026-08-24T00:00:00Z&period_to=2026-08-24T23:59:59Z" \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "visitors": 1,
  "sessions": 1,
  "product_views": 2,
  "cart_adds": 1,
  "checkouts": 1,
  "contacts": 1,
  "leads": 1,
  "orders_created": 1,
  "orders_paid": 1,
  "manual_sales": 0,
  "money": [
    {
      "currency": "EUR",
      "gross": "2499.0000",
      "refunds": "0.0000",
      "net": "2499.0000",
      "aov": "2499.0000"
    }
  ],
  "session_to_lead": "1.0000",
  "session_to_paid_sale": "1.0000",
  "lead_to_paid_sale": "1.0000",
  "checkout_to_paid_order": "1.0000",
  "first_visit_to_lead_seconds": "3600",
  "first_visit_to_paid_sale_seconds": "7200"
}
```

Если знаменатель конверсии равен нулю, соответствующее поле — `null`.

### Errors

| Status | Description |
| ------ | ----------- |
| `400` | `period_from` must be `<= period_to` |
| `401` | Missing or invalid read API key |
| `422` | Invalid query parameter |

---

# GET /api/v1/analytics/funnel

Ecommerce-воронка и Lead-воронка. На каждом шаге — количество сущностей и конверсия к предыдущему шагу.

Ecommerce:

```text
session → product_view → add_to_cart → checkout_started → order_created → order_paid
```

Lead:

```text
session → contact_intent → contact_received → lead_created → lead_won → paid_sale
```

`lead_won` не является Sale. Paid sale — оплаченный Order с Lead или подтверждённая Manual Sale.

### Example

```bash
curl "http://localhost:8002/api/v1/analytics/funnel?period_from=2026-08-24T00:00:00Z&period_to=2026-08-24T23:59:59Z" \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "ecommerce": [
    { "key": "session", "count": 1, "conversion_from_previous": null },
    { "key": "product_view", "count": 1, "conversion_from_previous": "1.0000" },
    { "key": "add_to_cart", "count": 1, "conversion_from_previous": "1.0000" },
    { "key": "checkout_started", "count": 1, "conversion_from_previous": "1.0000" },
    { "key": "order_created", "count": 1, "conversion_from_previous": "1.0000" },
    { "key": "order_paid", "count": 1, "conversion_from_previous": "1.0000" }
  ],
  "lead": [
    { "key": "session", "count": 1, "conversion_from_previous": null },
    { "key": "contact_intent", "count": 1, "conversion_from_previous": "1.0000" },
    { "key": "contact_received", "count": 1, "conversion_from_previous": "1.0000" },
    { "key": "lead_created", "count": 1, "conversion_from_previous": "1.0000" },
    { "key": "lead_won", "count": 1, "conversion_from_previous": "1.0000" },
    { "key": "paid_sale", "count": 1, "conversion_from_previous": "1.0000" }
  ]
}
```

### Errors

Те же, что у overview: `400`, `401`, `422`.

---

# GET /api/v1/analytics/sources

Источники и кампании. Строки группируются по `source` и `campaign` выбранной attribution model.

### Example

```bash
curl "http://localhost:8002/api/v1/analytics/sources?period_from=2026-08-24T00:00:00Z&period_to=2026-08-24T23:59:59Z&attribution_model=last_non_direct" \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "items": [
    {
      "source": "google_ads",
      "campaign": "sofas-de-2026",
      "visitors": 1,
      "sessions": 1,
      "contacts": 1,
      "leads": 1,
      "orders_created": 1,
      "orders_paid": 1,
      "manual_sales": 0,
      "money": [
        {
          "currency": "EUR",
          "gross": "2499.0000",
          "refunds": "0.0000",
          "net": "2499.0000",
          "aov": "2499.0000"
        }
      ],
      "session_to_lead": "1.0000",
      "session_to_paid_sale": "1.0000",
      "lead_to_paid_sale": "1.0000",
      "first_visit_to_lead_seconds": "3600",
      "first_visit_to_paid_sale_seconds": "7200"
    }
  ]
}
```

`attribution_model=first_touch` переключает бакеты на First Touch. Direct visit не затирает известный Last Non-Direct Touch.

### Errors

Те же, что у overview: `400`, `401`, `422`.

---

# GET /api/v1/analytics/contact-channels

Сравнение `form` / `email` / `whatsapp` / `phone`.

Contacts и Leads считаются отдельно: повторные обращения одного Lead не завышают число Leads.

### Example

```bash
curl "http://localhost:8002/api/v1/analytics/contact-channels?period_from=2026-08-24T00:00:00Z&period_to=2026-08-24T23:59:59Z" \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "items": [
    {
      "channel": "form",
      "intents": 0,
      "contacts": 2,
      "leads": 1,
      "orders_paid": 1,
      "manual_sales": 0,
      "money": [
        {
          "currency": "EUR",
          "gross": "2499.0000",
          "refunds": "0.0000",
          "net": "2499.0000",
          "aov": "2499.0000"
        }
      ],
      "contact_to_lead": "0.5000",
      "lead_to_paid_sale": "1.0000"
    }
  ]
}
```

### Errors

Те же, что у overview: `400`, `401`, `422`.

---

# GET /api/v1/analytics/products

Таблица SKU: просмотры, add to cart, orders, paid quantity, revenue, способы оплаты.

### Example

```bash
curl "http://localhost:8002/api/v1/analytics/products?period_from=2026-08-24T00:00:00Z&period_to=2026-08-24T23:59:59Z" \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "items": [
    {
      "sku": "SOFA-001",
      "views": 2,
      "cart_adds": 1,
      "orders_created": 1,
      "orders_paid": 1,
      "paid_quantity": 1,
      "money": [
        {
          "currency": "EUR",
          "gross": "2499.0000",
          "refunds": "0.0000",
          "net": "2499.0000",
          "aov": "2499.0000"
        }
      ],
      "view_to_paid_order": "0.5000",
      "payment_methods": ["paypal"]
    }
  ]
}
```

### Errors

Те же, что у overview: `400`, `401`, `422`.

---

# GET /api/v1/analytics/payment-methods

Доступность, выбор, ошибки и конверсия способов оплаты.

`selected_rate` = выборы / checkouts, где способ был **показан**. Нельзя оценивать способ только по числу заказов.

### Example

```bash
curl "http://localhost:8002/api/v1/analytics/payment-methods?period_from=2026-08-24T00:00:00Z&period_to=2026-08-24T23:59:59Z" \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "items": [
    {
      "payment_method": "paypal",
      "shown": 2,
      "selected": 1,
      "failed": 0,
      "selected_rate": "0.5000",
      "orders_created": 1,
      "orders_paid": 1,
      "selected_to_paid": "1.0000",
      "money": [
        {
          "currency": "EUR",
          "gross": "2499.0000",
          "refunds": "0.0000",
          "net": "2499.0000",
          "aov": "2499.0000"
        }
      ]
    }
  ]
}
```

### Errors

Те же, что у overview: `400`, `401`, `422`.

---

# GET /api/v1/analytics/period-comparison

Сравнить два периода: текущий (`period_from` / `period_to`) и предыдущий (`compare_from` / `compare_to`).

Ответ содержит overview обоих периодов, абсолютное и процентное изменение и то же для способов оплаты.

Сравнение показывает корреляцию, не причинность.

### Example

```bash
curl "http://localhost:8002/api/v1/analytics/period-comparison?period_from=2026-08-24T00:00:00Z&period_to=2026-08-24T23:59:59Z&compare_from=2026-08-17T00:00:00Z&compare_to=2026-08-17T23:59:59Z" \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "current": { "visitors": 1, "sessions": 1 },
  "previous": { "visitors": 0, "sessions": 0 },
  "delta": {
    "visitors": { "abs": 1, "pct": null },
    "sessions": { "abs": 1, "pct": null }
  },
  "payment_methods": {
    "current": [],
    "previous": [],
    "delta": []
  }
}
```

Полный пример: `contracts/http/examples/responses/period-comparison.json`.

Если предыдущее значение равно нулю, `pct` равен `null`.

### Errors

| Status | Description |
| ------ | ----------- |
| `400` | `period_from` / `compare_from` больше конца периода, или нет `compare_from` / `compare_to` |
| `401` | Missing or invalid read API key |
| `422` | Invalid query parameter |

---

# GET /api/v1/analytics/journey/search

Найти сущности Journey по строке `q`.

`q` может быть:

* Visitor / Session UUID v4;
* Shopware hex ID (`lead`, `order`, `customer`, `contact`, `manual_sale`);
* номер заказа;
* GCLID / GBRAID / WBRAID;
* campaign;
* contact channel (`form`, `email`, `whatsapp`, `phone`);
* безопасный tracking reference.

### Example

```bash
curl "http://localhost:8002/api/v1/analytics/journey/search?q=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "items": [
    {
      "entity_type": "visitor",
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "sales_channel_id": "018f1a2b3c4d5e6f7890abcdef123456",
      "occurred_at": "2026-08-24T09:00:00Z"
    }
  ]
}
```

Пустой список — не ошибка: совпадений нет.

### Errors

| Status | Description |
| ------ | ----------- |
| `400` | `q` пустой после trim |
| `401` | Missing or invalid read API key |
| `422` | Invalid query parameter |

---

# GET /api/v1/analytics/visitors/{visitor_id}/journey

Хронологический путь Visitor. События отсортированы по `occurred_at`, затем `event_id`.

`visitor_id` — UUID v4.

### Example

```bash
curl http://localhost:8002/api/v1/analytics/visitors/550e8400-e29b-41d4-a716-446655440000/journey \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "events": [
    {
      "event_id": "2f1c3a50-fd24-4f2d-8dd4-42e82b5e9101",
      "event_type": "session_started",
      "occurred_at": "2026-08-24T09:00:00Z",
      "received_at": "2026-08-24T09:00:01Z",
      "source": "nextjs",
      "sales_channel_id": "018f1a2b3c4d5e6f7890abcdef123456",
      "visitor_id": "550e8400-e29b-41d4-a716-446655440000",
      "session_id": "9b1de427-512a-482e-a2bf-66d1f6de06e3",
      "lead_id": null,
      "customer_id": null,
      "order_id": null,
      "contact_id": null,
      "manual_sale_id": null,
      "refund_id": null,
      "payload": {
        "landing_page": "https://www.jvmoebel.de/sofas/sofa-001",
        "utm": {
          "utm_campaign": "sofas-de-2026"
        }
      }
    }
  ]
}
```

### Errors

| Status | Description |
| ------ | ----------- |
| `401` | Missing or invalid read API key |
| `404` | Journey not found |
| `422` | Invalid path identifier |

---

# GET /api/v1/analytics/leads/{lead_id}/journey

Путь Lead: события Lead, связанного Visitor, Order и Manual Sale.

`lead_id` — 32 hex символа Shopware ID.

### Example

```bash
curl http://localhost:8002/api/v1/analytics/leads/018f1111111111111111111111111111/journey \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Errors

Те же, что у visitor journey: `401`, `404`, `422`.

---

# GET /api/v1/analytics/orders/{order_id}/journey

Путь Order: события заказа, связанного Visitor, cart и Lead.

`order_id` — 32 hex символа Shopware ID.

### Example

```bash
curl http://localhost:8002/api/v1/analytics/orders/018f3333333333333333333333333333/journey \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Errors

Те же, что у visitor journey: `401`, `404`, `422`.

---

# GET /api/v1/analytics/customers/{customer_id}/journey

Объединённый путь Customer после `customer_linked`: исходные Visitor IDs и Sessions сохраняются.

`customer_id` — 32 hex символа Shopware ID.

### Example

```bash
curl http://localhost:8002/api/v1/analytics/customers/018f2222222222222222222222222222/journey \
  -H "Authorization: Bearer $ANALYTICS_READ_API_KEY"
```

### Errors

Те же, что у visitor journey: `401`, `404`, `422`.

---

# Analytics API error summary

| HTTP status | Когда возникает |
| ----------- | --------------- |
| `200` | Успешный ingest (в том числе duplicate того же события) или успешный read |
| `400` | Некорректный диапазон периода, нет `compare_from`/`compare_to`, пустой `q` |
| `401` | Отсутствует или неверный Bearer token |
| `404` | Journey не найден |
| `409` | HTTP ingest: тот же `event_id`, другое событие |
| `413` | HTTP request body превышает `MAX_BODY_SIZE` |
| `422` | Невалидная JSON Schema, неизвестный `sales_channel_id`, Origin/domain, Shopware type на HTTP, некорректный query/path |
| `429` | HTTP ingest rate limit exceeded |
| `500` | Необработанная внутренняя ошибка |
| `503` | Database schema не готова, например не применены Alembic migrations |

Для точного JSON error response ориентироваться на `app/core/errors_handlers.py`.

При превышении `MAX_BODY_SIZE` middleware возвращает:

```json
{
  "detail": "Request body too large"
}
```

OpenAPI приложения (`/docs`) содержит те же коды, что и таблицы выше.
