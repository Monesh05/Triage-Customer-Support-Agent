# app/tools/product.py
# Purpose: Product Agent tool layer (spec section 13): `search_product_docs`. Phase 6 replaces
#          the earlier keyword (ILIKE) stub with real pgvector semantic search (spec section 14)
#          over the knowledge_documents/knowledge_chunks tables via app.rag.retrieval, with
#          optional category/product metadata filtering and a minimum-similarity floor so an
#          irrelevant query returns no matches rather than a forced citation.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from app.database.session import get_session
from app.rag.retrieval import RetrievalError, search_knowledge
from app.tools.base import ToolResult
from app.tools.schemas import ProductDocMatchData, ProductDocSearchData

logger = logging.getLogger("clouddesk.tools.product")

MIN_QUERY_LENGTH: int = 1


async def search_product_docs(
    query: str, category: str | None = None, product: str | None = None
) -> ToolResult[ProductDocSearchData]:
    """Semantically search CloudDesk's product knowledge base for a query string.

    `category`/`product` are optional metadata filters (spec section 14) matching a
    knowledge document's `category`/`product` fields exactly (e.g. category="pricing").
    Returns `success=True` with an empty `matches` list when nothing clears the configured
    minimum-similarity threshold — that is a normal outcome, never an error.
    """
    try:
        if len(query.strip()) < MIN_QUERY_LENGTH:
            return ToolResult(success=False, error="query must not be empty")

        async with get_session() as session:
            results = await search_knowledge(
                session, query.strip(), category=category, product=product
            )
        matches = [
            ProductDocMatchData(
                document_id=m.document_id,
                title=m.title,
                category=m.category,
                product=m.product,
                version=m.version,
                source=m.source,
                updated_at=m.updated_at,
                chunk_text=m.chunk_text,
                score=m.score,
            )
            for m in results
        ]
        data = ProductDocSearchData(query=query, category=category, product=product, matches=matches)
        return ToolResult(success=True, data=data)
    except RetrievalError as exc:
        logger.warning("search_product_docs_retrieval_failed error=%s", exc)
        return ToolResult(success=False, error=f"Product knowledge search failed: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.exception("search_product_docs_unexpected_error")
        return ToolResult(success=False, error=f"Unexpected error in search_product_docs: {exc}")
