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

Host HTTP: `8003` (dev, `PORT_DEV`). Prod: `8002` (`PORT`).

Prod / dev / test — разные compose-проекты (`analytics`, `analytics-dev`, `analytics-test`). `down` одного файла остальные стеки не трогает.

## Тесты
```bash
cp .env.test.example .env.test
docker compose --env-file .env.test -f docker-compose.test.yml up -d
uv run pytest
```
