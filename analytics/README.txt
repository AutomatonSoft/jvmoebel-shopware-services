# Analytics service

Команды запускать из каталога `analytics/`.

## Установка зависимостей
```bash
uv sync
```

## Запуск приложения
```bash
cp .env.example .env
cp .env.dev.example .env.dev
docker compose --env-file .env.dev -f docker-compose.dev.yml up --build

docker compose --env-file .env.dev -f docker-compose.dev.yml exec backend_dev uv run alembic revision --autogenerate -m "description"
docker compose --env-file .env.dev -f docker-compose.dev.yml exec backend_dev uv run alembic upgrade head
```

Host HTTP: `8003` (dev, `PORT_DEV`). Local compose: `127.0.0.1:8002` (`PORT`). Production: Nginx → `analytics-backend:8000`, без host port.

Prod / dev / test — разные compose-проекты (`analytics`, `analytics-dev`, `analytics-test`). `down` одного файла остальные стеки не трогает.

После смены RabbitMQ vhost или users нужен `docker compose down -v`: `RABBITMQ_DEFAULT_*` применяется только на пустом volume брокера.

## Тесты
```bash
cp .env.test.example .env.test
docker compose --env-file .env.test -f docker-compose.test.yml up -d
uv run pytest
```
