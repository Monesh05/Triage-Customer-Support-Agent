# app/rag/ingest.py
# Purpose: Product RAG ingestion pipeline (spec section 14): loads knowledge-base documents,
#          chunks them, embeds each chunk, and upserts them into knowledge_documents /
#          knowledge_chunks. Idempotent — re-running deletes and re-inserts a document's chunks
#          by document_id rather than duplicating rows. Runnable as a CLI:
#              python -m app.rag.ingest
#          (from clouddesk/backend, with the venv active and DATABASE_URL pointing at Postgres).
#          Mirrors data/seed/seed.py's convention of logging progress (not print()).
# Author: CloudDesk Team
# Date: 2026-09-24

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging
from app.database.session import get_session
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag.chunking import chunk_text
from app.rag.documents import ParsedDocument, load_knowledge_documents
from app.rag.embeddings import embed_texts

logger = logging.getLogger("clouddesk.rag.ingest")

KNOWLEDGE_DIR: Path = Path(__file__).resolve().parents[3] / "data" / "knowledge"

EmbedFn = Callable[[list[str]], Awaitable[list[list[float]]]]


class IngestError(Exception):
    """Raised when a document fails to ingest (chunking/embedding/DB failure)."""


@dataclass(frozen=True)
class IngestSummary:
    """Result of an ingestion run."""

    documents_ingested: int
    chunks_ingested: int


async def _upsert_document(session: AsyncSession, parsed: ParsedDocument) -> KnowledgeDocument:
    """Insert or update a KnowledgeDocument row by its unique `document_id`."""
    result = await session.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.document_id == parsed.document_id)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        document = KnowledgeDocument(
            document_id=parsed.document_id,
            title=parsed.title,
            category=parsed.category,
            product=parsed.product,
            version=parsed.version,
            source=parsed.source,
            source_updated_at=parsed.updated_at,
            content=parsed.content,
        )
        session.add(document)
    else:
        existing.title = parsed.title
        existing.category = parsed.category
        existing.product = parsed.product
        existing.version = parsed.version
        existing.source = parsed.source
        existing.source_updated_at = parsed.updated_at
        existing.content = parsed.content
        document = existing
    await session.flush()
    return document


async def _replace_chunks(
    session: AsyncSession, document: KnowledgeDocument, parsed: ParsedDocument, embed_fn: EmbedFn
) -> int:
    """Delete this document's existing chunks and insert freshly chunked+embedded ones."""
    await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))

    pieces = chunk_text(parsed.content)
    if not pieces:
        raise IngestError(f"{parsed.document_id}: chunking produced zero chunks")

    try:
        embeddings = await embed_fn(pieces)
    except Exception as exc:  # noqa: BLE001 - re-raised as a typed ingestion error
        raise IngestError(f"{parsed.document_id}: embedding failed: {exc}") from exc

    session.add_all(
        KnowledgeChunk(
            document_id=document.id, chunk_index=index, content=piece, embedding=embedding
        )
        for index, (piece, embedding) in enumerate(zip(pieces, embeddings, strict=True))
    )
    await session.flush()
    return len(pieces)


async def ingest_documents(
    session: AsyncSession, documents: list[ParsedDocument], embed_fn: EmbedFn = embed_texts
) -> IngestSummary:
    """Ingest every parsed document into the knowledge base tables (idempotent per document)."""
    total_chunks = 0
    for parsed in documents:
        document = await _upsert_document(session, parsed)
        chunk_count = await _replace_chunks(session, document, parsed, embed_fn)
        total_chunks += chunk_count
        logger.info("ingested_document document_id=%s chunks=%d", parsed.document_id, chunk_count)
    return IngestSummary(documents_ingested=len(documents), chunks_ingested=total_chunks)


async def run_ingest() -> IngestSummary:
    """Load every knowledge-base document from disk and ingest it. Entry point for the CLI."""
    documents = load_knowledge_documents(KNOWLEDGE_DIR)
    async with get_session() as session:
        summary = await ingest_documents(session, documents)
        await session.commit()
    logger.info(
        "ingest_complete documents=%d chunks=%d",
        summary.documents_ingested,
        summary.chunks_ingested,
    )
    return summary


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_ingest())
