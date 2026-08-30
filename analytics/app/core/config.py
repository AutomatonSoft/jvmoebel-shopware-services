# app/core/config.py

import os
from pathlib import Path

from pydantic import BaseModel, Field, Json, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    database: str = os.getenv("POSTGRES_DB", "jvmoebel_analytics_db")
    echo: bool = False

    @property
    def url(self) -> str:
        return (
            f"postgresql+{self.driver}://"
            f"{self.user}:{self.password}@"
            f"{self.host}:{self.port}/"
            f"{self.database}"
        )


# -------------------------
# RABBITMQ
# -------------------------
class RabbitMqSettings(BaseModel):
    url: str = os.getenv(
        "RABBITMQ_URL",
        "amqp://guest:guest@localhost:5672/",
    )
    events_queue: str = os.getenv(
        "RABBITMQ_EVENTS_QUEUE",
        "analytics.shopware.events",
    )


# -------------------------
# SALES CHANNELS
# -------------------------
class SalesChannelSettings(BaseModel):
    id: str
    origins: list[str] = Field(default_factory=list)
    market_code: str


# -------------------------
# SETTINGS
# -------------------------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_v1_prefix: str = "/api/v1"

    db: DbSettings = DbSettings()
    rabbitmq: RabbitMqSettings = RabbitMqSettings()

    analytics_ingest_api_key: SecretStr = Field(
        min_length=1,
        description="API key for event ingestion from Next.js",
    )
    analytics_read_api_key: SecretStr = Field(
        min_length=1,
        description="API key for dashboard read API",
    )
    sales_channels: Json[list[SalesChannelSettings]] = Field(
        default_factory=list,
        description="Allowlist of sales channels (id, origins, market_code)",
    )


settings: Settings = Settings()  # type: ignore[call-arg]
