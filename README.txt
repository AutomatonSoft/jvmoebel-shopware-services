# jvmoebel-services

## Установка зависимостей
```bash
uv sync
```

## Запуск приложения
```bash
cp .env.example .env
docker compose --env-file .env.dev -f docker-compose.dev.yml up --build

docker compose --env-file .env.dev -f docker-compose.dev.yml exec backend uv run alembic revision --autogenerate -m "description"
docker compose --env-file .env.dev -f docker-compose.dev.yml exec backend uv run alembic upgrade head
```

## Тесты
```bash
cp .env.test.example .env.test
docker compose --env-file .env.test -f docker-compose.test.yml up
uv run pytest
```