# jvmoebel-services

Репозиторий сервисов.

- [AR API](ar/README.md) — работа из каталога `ar/`, команды в [`ar/README.txt`](ar/README.txt)
- [Analytics API](analytics/README.md) — работа из каталога `analytics/`, команды в [`analytics/README.txt`](analytics/README.txt)

Команды из корня — в [`README.txt`](README.txt).

**Deploy.** Workflow `AR Deploy stage` проверяет и выкладывает только AR (`ar/compose.deploy.yml`, артефакт из `ar/`). Analytics в этот pipeline не входит: зелёный AR Deploy не означает, что Analytics задеплоен. Готовность Analytics к выкладке проверяет CI job `Analytics deployment validation` (compose, image, миграции, backend, worker). На сервер Analytics этим workflow не уезжает.

Внутри контейнеров API слушает `8000`, Postgres — `5432`, RabbitMQ — `5672` / `15672`. Ниже — порты на хосте.

## Production ports

`.env.example` / `docker-compose.yml`

| Service | HTTP (`PORT`) | Postgres (`POSTGRES_EXTERNAL_PORT`) | RabbitMQ AMQP | RabbitMQ management |
| ------- | ------------- | ----------------------------------- | ------------- | ------------------- |
| AR | `8000` | `5435` | — | — |
| Analytics | `8002` | `5438` | `5674` | `15674` |

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
