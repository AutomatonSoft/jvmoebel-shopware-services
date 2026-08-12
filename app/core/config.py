# app/core/config.py

from pathlib import Path

from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings

import os

BASE_DIR = Path(__file__).parent.parent


# -------------------------
# DATABASE
# -------------------------
class DbSettings(BaseModel):
    driver: str = "asyncpg"
    user: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", 5432))
    database: str = os.getenv("POSTGRES_DB", "jvmoebel_db")
    echo: bool = False  # вывод SQL-запросов в консоль

    @property
    def url(self) -> str:
        return (
            f"postgresql+{self.driver}://"
            f"{self.user}:{self.password}@"
            f"{self.host}:{self.port}/"
            f"{self.database}"
        )


# -------------------------
# SETTINGS
# -------------------------
class Settings(BaseSettings):
    api_v1_prefix: str = "/api/v1"

    db: DbSettings = DbSettings()
    # db_echo: bool = True


# single instance
settings = Settings()
