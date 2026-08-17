# jvmoebel-services

## Установка зависимостей
uv sync

## Запуск приложения
cp .env.example .env
docker-compose up --build
docker exec jvmoebel_backend uv run alembic upgrade head

## Тесты
cp .env.test.example .env.test
docker compose --env-file .env.test -f docker-compose.test.yml up -d
uv run pytest