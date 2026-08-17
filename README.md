# jvmoebel-services

## Установка зависимостей
```bash
uv sync
```

## Запуск приложения
```bash
cp .env.example .env
docker-compose up --build
docker exec jvmoebel_backend uv run alembic upgrade head
```

## Тесты
```bash
cp .env.test.example .env.test
docker compose --env-file .env.test -f docker-compose.test.yml up -d
uv run pytest
```
