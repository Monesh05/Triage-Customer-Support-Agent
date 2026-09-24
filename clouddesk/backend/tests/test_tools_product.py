# tests/test_tools_product.py
# Purpose: Tests for app.tools.product — search_product_docs, now backed by Phase 6 pgvector
#          semantic search (app.rag.retrieval) instead of the earlier keyword-search stub.
#          Mocks app.tools.product.search_knowledge's embedding dependency indirectly by
#          monkeypatching app.rag.embeddings.embed_query, so no live OpenAI call is made.
# Author: CloudDesk Team
# Date: 2026-09-24

import datetime

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.tools import product

_DOCUMENT_ID = "test-tool-product-doc"
_EMBEDDING_DIM = 1536


def _unit_vector(axis: int) -> list[float]:
    vector = [0.0] * _EMBEDDING_DIM
    vector[axis] = 1.0
    return vector


async def _seed_document(session: AsyncSession) -> None:
    document = KnowledgeDocument(
        document_id=_DOCUMENT_ID,
        title="Two-Factor Auth Toolkit",
        category="feature documentation",
        product="CloudDesk Platform",
        version="1.0",
        source="tests/fixture.md",
        source_updated_at=datetime.date(2026, 1, 1),
        content="Enables MFA / two-factor login for accounts.",
    )
    session.add(document)
    await session.flush()
    session.add(
        KnowledgeChunk(
            document_id=document.id,
            chunk_index=0,
            content="Enables MFA / two-factor login for accounts.",
            embedding=_unit_vector(0),
        )
    )
    await session.commit()


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(delete(KnowledgeDocument).where(KnowledgeDocument.document_id == _DOCUMENT_ID))
    await session.commit()


async def test_search_product_docs_returns_metadata_rich_match(
    committed_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_document(committed_session)

    async def fake_embed_query(_: str) -> list[float]:
        return _unit_vector(0)

    monkeypatch.setattr("app.rag.embeddings.embed_query", fake_embed_query)

    try:
        result = await product.search_product_docs("two-factor authentication")

        assert result.success is True
        assert len(result.data.matches) == 1
        match = result.data.matches[0]
        assert match.document_id == _DOCUMENT_ID
        assert match.title == "Two-Factor Auth Toolkit"
        assert match.category == "feature documentation"
        assert match.score == pytest.approx(1.0)
        assert "MFA" in match.chunk_text
    finally:
        await _cleanup(committed_session)


async def test_search_product_docs_no_match_returns_empty_list_not_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_embed_query(_: str) -> list[float]:
        return _unit_vector(1)  # orthogonal to anything seeded elsewhere in this test run

    monkeypatch.setattr("app.rag.embeddings.embed_query", fake_embed_query)

    result = await product.search_product_docs("zzz_no_such_feature_zzz")

    assert result.success is True
    assert result.data.matches == []


async def test_search_product_docs_rejects_empty_query() -> None:
    result = await product.search_product_docs("   ")

    assert result.success is False


async def test_search_product_docs_filters_by_category(
    committed_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _seed_document(committed_session)

    async def fake_embed_query(_: str) -> list[float]:
        return _unit_vector(0)

    monkeypatch.setattr("app.rag.embeddings.embed_query", fake_embed_query)

    try:
        result = await product.search_product_docs("mfa", category="pricing")

        assert result.success is True
        assert result.data.matches == []
    finally:
        await _cleanup(committed_session)
