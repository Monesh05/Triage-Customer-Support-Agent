# app/llm/client.py
# Purpose: Thin, provider-agnostic wrapper around the OpenAI Python SDK's AsyncOpenAI client.
#          Selects "openai" (direct) or "openrouter" (OpenAI-compatible gateway) based on
#          Settings.llm_provider, so agent/tool-loop code never hardcodes a provider, base URL,
#          or model name (spec section 4: model must be configurable via environment variables).
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
from dataclasses import dataclass
from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import Settings, get_settings

logger = logging.getLogger("clouddesk.llm")

OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
PROVIDER_OPENAI: str = "openai"
PROVIDER_OPENROUTER: str = "openrouter"


@dataclass(frozen=True)
class LLMClient:
    """Bundles a configured AsyncOpenAI client with the model name/provider to use for calls."""

    client: AsyncOpenAI
    model: str
    provider: str


def _build_openai_client(settings: Settings) -> LLMClient:
    """Build the LLMClient for LLM_PROVIDER=openai (direct OpenAI API)."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    return LLMClient(client=client, model=settings.openai_model, provider=PROVIDER_OPENAI)


def _build_openrouter_client(settings: Settings) -> LLMClient:
    """Build the LLMClient for LLM_PROVIDER=openrouter (OpenAI-compatible gateway)."""
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=OPENROUTER_BASE_URL,
    )
    return LLMClient(client=client, model=settings.openrouter_model, provider=PROVIDER_OPENROUTER)


@lru_cache
def get_llm_client() -> LLMClient:
    """Return a cached, provider-configured LLM client based on the current settings.

    Raises:
        ValueError: if llm_provider is unrecognized or its API key is missing.
    """
    settings = get_settings()
    if settings.llm_provider == PROVIDER_OPENAI:
        llm = _build_openai_client(settings)
    elif settings.llm_provider == PROVIDER_OPENROUTER:
        llm = _build_openrouter_client(settings)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider!r}")

    logger.debug("llm_client_configured provider=%s model=%s", llm.provider, llm.model)
    return llm
