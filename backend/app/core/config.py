"""Application configuration.

Единая точка входа для всех переменных окружения. Ничто в проекте не должно
читать os.environ напрямую — только через Settings, чтобы конфигурация была
валидируемой и типизированной (см. docs/01-architecture-and-design.md, 1.6).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "TaskFlow API"
    environment: str = Field(default="local")  # local | staging | production
    debug: bool = Field(default=True)
    api_v1_prefix: str = "/api/v1"

    # --- Security ---
    # NOTE: не подставляй значение по умолчанию в проде — .env.example
    # содержит placeholder, реальный секрет задаётся через окружение.
    jwt_secret_key: str = Field(default="CHANGE_ME_IN_ENV")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # --- Database (реальное подключение — Этап 4) ---
    database_url: str = Field(
        default="postgresql+asyncpg://taskflow:taskflow@localhost:5432/taskflow"
    )

    # --- Redis (кэш, pub/sub, брокер Celery) ---
    redis_url: str = Field(default="redis://localhost:6379/0")

    # --- CORS ---
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- AI (Этап 10) ---
    ai_provider: str = Field(default="openai")
    openai_api_key: str | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    """Кэшированный singleton — Settings читается один раз за процесс."""
    return Settings()
