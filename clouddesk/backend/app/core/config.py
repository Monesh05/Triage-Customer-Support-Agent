# app/core/config.py
# Purpose: Central application settings loaded from environment variables via pydantic-settings.
#          Provides configuration for the database connection, API metadata, LLM/OpenRouter
#          integration, the Phase 6 Product RAG embeddings/retrieval pipeline (spec
#          section 14) — embedding model name and retrieval tuning are never hardcoded at
#          call sites, only read from here — (Phase 9, spec section 25) the CORS allowed-
#          origins list a frontend dev server needs to call this API from a different origin, and
#          (Phase 10, spec section 27) the JWT signing secret/expiry and rate-limit thresholds.
#          The JWT secret has NO hardcoded default in a non-development environment: see
#          `jwt_secret_key`'s validation in `get_settings()`.
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

    # Phase 9 (spec section 25): comma-separated list of origins allowed to call this API from a
    # browser (the Next.js frontend). Configurable via env rather than hardcoded so a deployed
    # frontend's real origin can be added without a code change; the default covers the two most
    # common local dev ports for a separate frontend process.
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- Phase 10 authentication (spec section 27) ---
    # Signing secret for customer/staff login JWTs (app.core.security). MUST be overridden via the
    # JWT_SECRET_KEY env var outside local development — see the non-default-value check below.
    # The literal below is intentionally obviously-a-placeholder, never a real secret, and is only
    # ever used when app_env == "development" (e.g. a fresh dev checkout with no .env yet).
    jwt_secret_key: str = "dev-only-insecure-default-change-me"
    jwt_algorithm: str = "HS256"
    # Short-lived per org policy A07 ("short-lived tokens, enforce expiry"). A customer/staff
    # session simply logs in again once expired; there is no refresh-token flow in this phase's
    # scope (a demo/portfolio B2B SaaS, not a system with long-lived user sessions).
    jwt_access_token_expire_minutes: int = 30

    # --- Phase 10 rate limiting (spec section 27) ---
    # Per-client (by authenticated identity, falling back to source IP) request budgets on the two
    # most cost/abuse-sensitive endpoints: starting a conversation (a real LLM call chain costing
    # real money per request) and login (brute-force protection). Expressed as slowapi/`limits`
    # syntax strings ("<count>/<period>").
    rate_limit_login: str = "5/minute"
    rate_limit_conversations: str = "10/minute"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        """`cors_allowed_origins` split into a clean list, ignoring blank/whitespace entries."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


_INSECURE_DEFAULT_JWT_SECRET: str = "dev-only-insecure-default-change-me"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance to avoid re-parsing the environment repeatedly.

    Refuses to start in a non-development environment with the placeholder JWT secret still in
    place (org policy: never hardcode secrets / A07 token integrity depends entirely on this
    value being kept private, which an in-repo default cannot be).
    """
    settings = Settings()
    if settings.app_env != "development" and settings.jwt_secret_key == _INSECURE_DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to a real secret when APP_ENV is not 'development'."
        )
    return settings
