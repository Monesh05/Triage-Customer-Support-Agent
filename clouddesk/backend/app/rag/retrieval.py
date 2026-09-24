# app/rag/retrieval.py
# Purpose: pgvector semantic search over the Product RAG knowledge base (spec section 14).
#          Embeds the query, runs a parameterized cosine-similarity search (via pgvector's
#          SQLAlchemy Comparator, never raw SQL string formatting), optionally filtered by
#          category/product metadata, and applies a minimum-similarity threshold so an
#          unrelated query returns no matches rather than a forced, low-quality citation.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
from collections.abc import Awaitable, Callable

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag import embeddings
from app.rag.embeddings import EmbeddingError

logger = logging.getLogger("clouddesk.rag.retrieval")

EmbedQueryFn = Callable[[str], Awaitable[list[float]]]


class RetrievalError(Exception):
    """Raised when semantic retrieval cannot be completed (embedding or query failure)."""


class KnowledgeMatch(BaseModel):
    """A single retrieved knowledge-base chunk with its full spec-section-14 source metadata."""

    document_id: str
    title: str
    category: str
    product: str
    version: str
    source: str
    updated_at: str
    chunk_text: str
    score: float


async def search_knowledge(
    session: AsyncSession,
    query: str,
    *,
    category: str | None = None,
    product: str | None = None,
    top_k: int | None = None,
    embed_query_fn: EmbedQueryFn | None = None,
) -> list[KnowledgeMatch]:
    """Semantically search the knowledge base for chunks relevant to `query`.

    Applies `Settings.rag_min_similarity` as a hard floor: chunks below that cosine
    similarity are excluded, never returned as a forced/low-quality match. Returns matches
    ordered by descending similarity (best first).

    `embed_query_fn` defaults to `app.rag.embeddings.embed_query`, looked up dynamically (via
    the module, not a bound default) so tests can monkeypatch `app.rag.embeddings.embed_query`
    without having to pass this parameter explicitly.

    Raises:
        RetrievalError: if embedding the query fails.
    """
    settings = get_settings()
    effective_top_k = top_k if top_k is not None else settings.rag_top_k
    embed_fn = embed_query_fn if embed_query_fn is not None else embeddings.embed_query
    try:
        query_embedding = await embed_fn(query)
    except EmbeddingError as exc:
        raise RetrievalError(f"Failed to embed query: {exc}") from exc

    distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)
    max_distance = 1.0 - settings.rag_min_similarity

    stmt = (
        select(KnowledgeChunk, KnowledgeDocument, distance.label("distance"))
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(distance <= max_distance)
        .order_by(distance)
        .limit(effective_top_k)
    )
    if category is not None:
        stmt = stmt.where(KnowledgeDocument.category == category)
    if product is not None:
        stmt = stmt.where(KnowledgeDocument.product == product)

    try:
        rows = (await session.execute(stmt)).all()
    except Exception as exc:  # noqa: BLE001 - DB-layer failure surfaced as a typed error
        logger.warning("knowledge_search_failed error=%s", exc)
        raise RetrievalError(f"Knowledge search query failed: {exc}") from exc

    return [
        KnowledgeMatch(
            document_id=doc.document_id,
            title=doc.title,
            category=doc.category,
            product=doc.product,
            version=doc.version,
            source=doc.source,
            updated_at=doc.source_updated_at.isoformat(),
            chunk_text=chunk.content,
            score=round(1.0 - row_distance, 4),
        )
        for chunk, doc, row_distance in rows
    ]
