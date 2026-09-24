# tests/test_rag_ingest.py
# Purpose: Tests for app.rag.chunking (pure, no DB/API needed) and app.rag.ingest (real Postgres
#          test DB via `committed_session`, mocked embeddings client — no live OpenAI calls).
#          Covers chunk-boundary overlap, metadata landing correctly on KnowledgeDocument rows,
#          and idempotent re-ingestion (no duplicate chunk rows on a second run).
# Author: CloudDesk Team
# Date: 2026-09-24

import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag.chunking import chunk_text
from app.rag.documents import ParsedDocument
from app.rag.ingest import ingest_documents

_EMBEDDING_DIM = 1536
_TEST_DOCUMENT_ID = "test-ingest-doc"


def _fake_vector(seed: float) -> list[float]:
    return [seed] * _EMBEDDING_DIM


async def _fake_embed(texts: list[str]) -> list[list[float]]:
    return [_fake_vector(0.01 * (index + 1)) for index, _ in enumerate(texts)]


def test_chunk_text_empty_returns_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunk_text_short_content_is_a_single_chunk() -> None:
    content = "First paragraph.\n\nSecond paragraph."
    chunks = chunk_text(content, max_chars=900)
    assert len(chunks) == 1
    assert "First paragraph." in chunks[0]
    assert "Second paragraph." in chunks[0]


def test_chunk_text_splits_long_content_with_overlap() -> None:
    paragraphs = [f"Paragraph number {i} with enough text to add up quickly." for i in range(10)]
    content = "\n\n".join(paragraphs)

    chunks = chunk_text(content, max_chars=200)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 250  # allows the mandated one-paragraph overlap to slightly exceed
    # The overlap paragraph carried from chunk N into chunk N+1 must appear in both.
    first_chunk_paragraphs = chunks[0].split("\n\n")
    assert first_chunk_paragraphs[-1] in chunks[1]


def _sample_document(content: str) -> ParsedDocument:
    return ParsedDocument(
        document_id=_TEST_DOCUMENT_ID,
        title="Test Document",
        category="troubleshooting",
        product="CloudDesk API",
        version="1.0",
        source="tests/fixture.md",
        updated_at=datetime.date(2026, 1, 1),
        content=content,
    )


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(
        delete(KnowledgeDocument).where(KnowledgeDocument.document_id == _TEST_DOCUMENT_ID)
    )
    await session.commit()


async def test_ingest_documents_stores_metadata_and_chunks(
    committed_session: AsyncSession,
) -> None:
    content = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    parsed = _sample_document(content)

    try:
        summary = await ingest_documents(committed_session, [parsed], embed_fn=_fake_embed)
        await committed_session.commit()

        assert summary.documents_ingested == 1
        assert summary.chunks_ingested == len(chunk_text(content))

        result = await committed_session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.document_id == _TEST_DOCUMENT_ID)
        )
        document = result.scalar_one()
        assert document.title == "Test Document"
        assert document.category == "troubleshooting"
        assert document.product == "CloudDesk API"
        assert document.source == "tests/fixture.md"
        assert document.source_updated_at == datetime.date(2026, 1, 1)

        chunk_result = await committed_session.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id)
        )
        chunks = list(chunk_result.scalars().all())
        assert len(chunks) == len(chunk_text(content))
        assert len(chunks[0].embedding) == _EMBEDDING_DIM
    finally:
        await _cleanup(committed_session)


async def test_ingest_documents_is_idempotent(committed_session: AsyncSession) -> None:
    original_content = "Paragraph A.\n\nParagraph B.\n\nParagraph C."
    parsed = _sample_document(original_content)

    try:
        await ingest_documents(committed_session, [parsed], embed_fn=_fake_embed)
        await committed_session.commit()

        # Re-ingest the SAME document_id with different content; re-running must replace, not
        # accumulate, chunk rows.
        updated_content = "Only one paragraph now."
        updated_parsed = _sample_document(updated_content)
        await ingest_documents(committed_session, [updated_parsed], embed_fn=_fake_embed)
        await committed_session.commit()

        doc_result = await committed_session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.document_id == _TEST_DOCUMENT_ID)
        )
        documents = list(doc_result.scalars().all())
        assert len(documents) == 1  # no duplicate document row
        assert documents[0].content == updated_content

        chunk_result = await committed_session.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.document_id == documents[0].id)
        )
        chunks = list(chunk_result.scalars().all())
        assert len(chunks) == len(chunk_text(updated_content))
    finally:
        await _cleanup(committed_session)
