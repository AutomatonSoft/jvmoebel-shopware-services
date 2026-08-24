# app/core/config.py

from pathlib import Path

import os

from pydantic import BaseModel, SecretStr, Field
from pydantic_settings import BaseSettings


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

    ar_models_storage_path: Path = (
        BASE_DIR / "storage" / "ar_models"
    )

    ar_write_api_key: SecretStr = Field(
        description="API key for write operations on AR models",
    )

    ar_max_file_size: int = Field(
        default=15 * 1024 * 1024,
        description="Maximum file size in bytes for AR models",
        ge=1,
    )
    ar_max_body_size: int = Field(
        default=16 * 1024 * 1024,
        description=(
            "Maximum HTTP request body size for AR model uploads. "
            "This limit is slightly higher than the 15 MB maximum model file size "
            "to account for multipart/form-data overhead."
        ),
        ge=1,
    )

    @property
    def ar_max_file_size_label(self) -> str:
        max_size_mb = self.ar_max_file_size / (1024 * 1024)
        if max_size_mb.is_integer():
            return f"{int(max_size_mb)} MB"
        return f"{max_size_mb:.2f} MB"


# single instance

settings = Settings()
