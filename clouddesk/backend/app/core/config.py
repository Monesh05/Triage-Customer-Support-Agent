# app/core/config.py
# Purpose: Central application settings loaded from environment variables via pydantic-settings.
#          Provides configuration for the database connection, API metadata, LLM/OpenRouter
#          integration, and the Phase 6 Product RAG embeddings/retrieval pipeline (spec
#          section 14) — embedding model name and retrieval tuning are never hardcoded at
#          call sites, only read from here.
# Author: CloudDesk Team
# Date: 2026-09-24

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

    # LLM gateway configuration (Phase 3+). "openai" talks to OpenAI's API directly;
    # "openrouter" talks to OpenRouter as a model gateway. Both use an OpenAI-compatible
    # client, so switching providers only changes base_url/api_key/model, not call sites.
    llm_provider: str = "openrouter"

    openrouter_api_key: str = ""
    openrouter_model: str = ""

    openai_api_key: str = ""
    openai_model: str = ""

    # Phase 6 Product RAG (spec section 14). Embeddings always call OpenAI directly (via
    # openai_api_key above) regardless of `llm_provider`, since OpenRouter is a chat-completion
    # gateway and does not proxy the embeddings API.
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    rag_top_k: int = 5
    # Minimum cosine similarity (1 - cosine distance) a retrieved chunk must clear to be
    # considered a real match. Below this, the Product Agent must report "not found" rather
    # than cite a barely-related chunk as grounding.
    rag_min_similarity: float = 0.25

    account_lockout_threshold: int = DEFAULT_ACCOUNT_LOCKOUT_THRESHOLD


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance to avoid re-parsing the environment repeatedly."""
    return Settings()
