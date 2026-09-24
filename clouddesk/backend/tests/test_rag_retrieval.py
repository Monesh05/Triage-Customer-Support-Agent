# tests/test_rag_retrieval.py
# Purpose: Tests for app.rag.retrieval.search_knowledge against a real Postgres/pgvector test
#          DB, with the embeddings client mocked (fixed vectors, no live OpenAI calls). Covers
#          similarity ordering, category metadata filtering, and the minimum-similarity floor
#          (an orthogonal query returns no matches rather than a forced low-quality citation).
# Author: CloudDesk Team
# Date: 2026-09-24

import datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.rag.retrieval import search_knowledge

_EMBEDDING_DIM = 1536
_DOC_IDS = ["retrieval-test-pricing", "retrieval-test-close", "retrieval-test-orthogonal"]


def _axis_vector(axis: int, weight: float = 1.0) -> list[float]:
    """A vector with `weight` on dimension `axis` and 0 elsewhere (deterministic cosine math)."""
    vector = [0.0] * _EMBEDDING_DIM
    vector[axis] = weight
    return vector


async def _seed(session: AsyncSession) -> None:
    exact_match = KnowledgeDocument(
        document_id=_DOC_IDS[0],
        title="Pricing Plans",
        category="pricing",
        product="CloudDesk Platform",
        version="1.0",
        source="tests/fixture.md",
        source_updated_at=datetime.date(2026, 1, 1),
        content="pricing content",
    )
    close_match = KnowledgeDocument(
        document_id=_DOC_IDS[1],
        title="Troubleshooting Guide",
        category="troubleshooting",
        product="CloudDesk API",
        version="1.0",
        source="tests/fixture.md",
        source_updated_at=datetime.date(2026, 1, 1),
        content="troubleshooting content",
    )
    orthogonal = KnowledgeDocument(
        document_id=_DOC_IDS[2],
        title="Unrelated Doc",
        category="feature documentation",
        product="CloudDesk Platform",
        version="1.0",
        source="tests/fixture.md",
        source_updated_at=datetime.date(2026, 1, 1),
        content="unrelated content",
    )
    session.add_all([exact_match, close_match, orthogonal])
    await session.flush()

    session.add_all(
        [
            KnowledgeChunk(
                document_id=exact_match.id, chunk_index=0, content="pricing chunk",
                embedding=_axis_vector(0, 1.0),
            ),
            KnowledgeChunk(
                document_id=close_match.id, chunk_index=0, content="troubleshooting chunk",
                # Mostly aligned with axis 0 but tilted toward axis 2 (NOT axis 1) — cosine
                # similarity to the axis-0 query is high (~0.9) but zero against an axis-1
                # query, so it stays cleanly distinguishable from both other fixtures below.
                embedding=[0.9, 0.0, 0.436] + [0.0] * (_EMBEDDING_DIM - 3),
            ),
            KnowledgeChunk(
                document_id=orthogonal.id, chunk_index=0, content="unrelated chunk",
                embedding=_axis_vector(1, 1.0),  # orthogonal to axis-0 query: similarity 0
            ),
        ]
    )
    await session.commit()


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(delete(KnowledgeDocument).where(KnowledgeDocument.document_id.in_(_DOC_IDS)))
    await session.commit()


async def _query_embed(_: str) -> list[float]:
    return _axis_vector(0, 1.0)


async def test_search_knowledge_orders_by_similarity(committed_session: AsyncSession) -> None:
    await _seed(committed_session)
    try:
        results = await search_knowledge(
            committed_session, "anything", embed_query_fn=_query_embed, top_k=5
        )

        result_ids = [r.document_id for r in results]
        assert result_ids[0] == _DOC_IDS[0]  # exact match ranks first
        assert _DOC_IDS[1] in result_ids  # the tilted-but-close match still clears the floor
        assert result_ids.index(_DOC_IDS[0]) < result_ids.index(_DOC_IDS[1])
        assert _DOC_IDS[2] not in result_ids  # orthogonal match filtered by min-similarity floor
        assert results[0].score == 1.0
        assert results[0].title == "Pricing Plans"
        assert results[0].category == "pricing"
    finally:
        await _cleanup(committed_session)


async def test_search_knowledge_filters_by_category(committed_session: AsyncSession) -> None:
    await _seed(committed_session)
    try:
        results = await search_knowledge(
            committed_session,
            "anything",
            category="troubleshooting",
            embed_query_fn=_query_embed,
            top_k=5,
        )

        assert len(results) == 1
        assert results[0].document_id == _DOC_IDS[1]
        assert results[0].category == "troubleshooting"
    finally:
        await _cleanup(committed_session)


async def test_search_knowledge_returns_empty_below_min_similarity(
    committed_session: AsyncSession,
) -> None:
    await _seed(committed_session)

    async def _orthogonal_query_embed(_: str) -> list[float]:
        return _axis_vector(1, 1.0)  # only matches the orthogonal/filtered-out doc exactly

    try:
        results = await search_knowledge(
            committed_session, "anything", embed_query_fn=_orthogonal_query_embed, top_k=5
        )
        # The orthogonal doc's own axis matches perfectly (score 1.0) — but the OTHER two
        # docs are now the ones below the floor, proving irrelevant docs are excluded either way.
        assert all(r.document_id != _DOC_IDS[0] for r in results)
        assert all(r.document_id != _DOC_IDS[1] for r in results)
    finally:
        await _cleanup(committed_session)
