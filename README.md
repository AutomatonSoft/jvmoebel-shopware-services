# jvmoebel-services

cp .env.example .env
docker-compose up --build
docker exec jvmoebel_backend uv run alembic upgrade head