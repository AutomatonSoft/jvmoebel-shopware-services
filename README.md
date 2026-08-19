# Docker и окружения

Проект поддерживает три окружения:

* **Production** — `docker-compose.yml`
* **Development** — `docker-compose.dev.yml`
* **Test** — `docker-compose.test.yml`

## 1. Файлы окружений

Используются отдельные environment-файлы:

```text
.env
.env.dev
.env.test
```

# Development

Development использует:

* `Dockerfile.dev`
* `docker-compose.dev.yml`
* bind mount исходников
* `uvicorn --reload`
* отдельный PostgreSQL volume
* отдельный AR storage volume

## Запуск

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml up
```

## Alembic в Development

В dev миграции запускаются вручную из backend-контейнера.

Применить все миграции:

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml exec backend uv run alembic upgrade head
```

Создать новую migration:

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yml exec backend uv run alembic revision --autogenerate -m "description"
```

# Production

Production использует:

* `Dockerfile`
* `docker-compose.yml`
* source code внутри Docker image
* Alembic migrations внутри Docker image
* отдельный `migrations` service
* persistent AR storage volume
* без bind mount
* без `--reload`


## Запуск

```bash
docker compose --env-file .env -f docker-compose.yml up -d
```


## Что происходит при запуске

Production запускается в следующем порядке:

```text
PostgreSQL
    ↓
healthcheck
    ↓
migrations
    ↓
alembic upgrade head
    ↓
backend
    ↓
uvicorn
```

Migration container завершает работу после успешного применения миграций.

Проверить состояние:

```bash
docker compose --env-file .env -f docker-compose.yml ps
```


## Production migrations

Посмотреть логи:

```bash
docker compose --env-file .env -f docker-compose.yml logs migrations
```

Если нужно вручную выполнить миграции:

```bash
docker compose --env-file .env -f docker-compose.yml run --rm migrations
```

Проверить текущую revision:

```bash
docker compose --env-file .env -f docker-compose.yml run --rm migrations uv run alembic current
```

## Production logs

Backend:

```bash
docker compose --env-file .env -f docker-compose.yml logs -f backend
```

PostgreSQL:

```bash
docker compose --env-file .env -f docker-compose.yml logs -f postgres_db
```

Все сервисы:

```bash
docker compose --env-file .env -f docker-compose.yml logs -f
```


# AR Storage

AR-файлы (`.glb`, `.usdz`) в production хранятся в Docker named volume:

```text
ar_models_data
```

Внутри контейнера storage доступен по адресу:

```text
/app/app/storage/ar_models
```

При этом production source code не содержит persistent AR data.

Схема:

```text
Docker image
├── /app/app
├── /app/alembic
└── /app/alembic.ini

Docker volume
└── ar_models_data
    └── /app/app/storage/ar_models
```


---

# PostgreSQL

Production PostgreSQL использует:

```text
postgres_data
```

Development PostgreSQL использует отдельный volume:

```text
postgres_data_dev
```
Test PostgreSQL использует отдельный volume:

```text
postgres_test_data
```


---

# Test

Для тестов используется:

```text
docker-compose.test.yml
```

Запуск:

```bash
docker compose --env-file .env.test -f docker-compose.test.yml up
```

---

# Pytest

Если тесты настроены на запуск непосредственно из локального Python environment:

```bash
uv run pytest
```

Запустить конкретный файл:

```bash
uv run pytest tests/ar/test_router.py
```

Запустить конкретный тест:

```bash
uv run pytest tests/ar/test_router.py::test_name
```

---

# Проверка Production Image

После сборки production image:

```bash
docker compose --env-file .env -f docker-compose.yml build
```

Проверить, что source code находится внутри image:

```bash
docker compose --env-file .env -f docker-compose.yml exec backend ls -la /app
```

Проверить application source:

```bash
docker compose --env-file .env -f docker-compose.yml exec backend ls -la /app/app
```

Проверить Alembic:

```bash
docker compose --env-file .env -f docker-compose.yml exec backend ls -la /app/alembic
```

Проверить отсутствие `--reload`:

```bash
docker compose --env-file .env -f docker-compose.yml logs backend
```

Проверить mounts:

```bash
docker inspect jvmoebel_backend --format '{{json .Mounts}}'
```

Production не должен иметь:

```text
.:/app
```

---