# app/core/config.py
# Purpose: Central application settings loaded from environment variables via pydantic-settings.
#          Provides configuration for the database connection, API metadata, and placeholders
#          for future LLM/OpenRouter integration (Phase 2+).
# Author: CloudDesk Team
# Date: 2026-09-21

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ACCOUNT_LOCKOUT_THRESHOLD: int = 5


class Settings(BaseSettings):
    """Application-wide configuration, sourced from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CloudDesk Backend"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+asyncpg://clouddesk:clouddesk@localhost:5432/clouddesk"
    )

    # Placeholders for later phases (LLM gateway via OpenRouter). Not used in Phase 1.
    openrouter_api_key: str = ""
    openrouter_model: str = ""

    account_lockout_threshold: int = DEFAULT_ACCOUNT_LOCKOUT_THRESHOLD


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance to avoid re-parsing the environment repeatedly."""
    return Settings()
