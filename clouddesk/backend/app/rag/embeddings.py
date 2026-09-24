# app/rag/embeddings.py
# Purpose: Thin async wrapper around OpenAI's embeddings API for Product RAG (spec section 14).
#          Always calls OpenAI directly via `openai_api_key` regardless of `llm_provider`,
#          since OpenRouter (the chat-completion gateway used elsewhere) does not proxy the
#          embeddings endpoint. Never lets a raw OpenAI SDK exception cross into app.rag.ingest
#          / app.rag.retrieval — everything is wrapped in a typed EmbeddingError.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
from functools import lru_cache

from openai import AsyncOpenAI, OpenAIError

from app.core.config import get_settings

logger = logging.getLogger("clouddesk.rag.embeddings")

MAX_EMBEDDING_BATCH_SIZE: int = 100


class EmbeddingError(Exception):
    """Raised when the embeddings API call fails or is misconfigured."""


@lru_cache
def _get_embedding_client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise EmbeddingError("OPENAI_API_KEY is required to generate embeddings")
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, preserving input order.

    Raises:
        EmbeddingError: if the API key is missing, the request fails, or the response shape
            is unexpected (never propagates a raw OpenAI SDK exception to callers).
    """
    if not texts:
        return []
    if len(texts) > MAX_EMBEDDING_BATCH_SIZE:
        raise EmbeddingError(
            f"Cannot embed {len(texts)} texts in one call (max {MAX_EMBEDDING_BATCH_SIZE})"
        )

    settings = get_settings()
    client = _get_embedding_client()
    try:
        response = await client.embeddings.create(
            model=settings.openai_embedding_model, input=texts
        )
    except OpenAIError as exc:
        logger.warning("embedding_request_failed error=%s", exc)
        raise EmbeddingError(f"Embedding request failed: {exc}") from exc

    if len(response.data) != len(texts):
        raise EmbeddingError(
            f"Embedding API returned {len(response.data)} vectors for {len(texts)} inputs"
        )
    ordered = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in ordered]


async def embed_query(query: str) -> list[float]:
    """Embed a single query string. Raises EmbeddingError under the same conditions as
    embed_texts."""
    vectors = await embed_texts([query])
    return vectors[0]
