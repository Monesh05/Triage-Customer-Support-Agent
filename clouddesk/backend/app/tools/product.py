# app/tools/product.py
# Purpose: Product Agent tool layer (spec section 13): `search_product_docs`. Implemented as
#          a plain keyword (ILIKE) search over app.models.product.Product's real name/
#          description fields via app.services.product_service — NOT the pgvector semantic
#          search / RAG pipeline described in spec section 14, which is a later phase.
# Author: CloudDesk Team
# Date: 2026-09-21

from app.database.session import get_session
from app.services import product_service
from app.tools.base import ToolResult
from app.tools.schemas import ProductDocMatchData, ProductDocSearchData

MIN_QUERY_LENGTH: int = 1


async def search_product_docs(query: str) -> ToolResult[ProductDocSearchData]:
    """Keyword-search CloudDesk product/feature descriptions for a query string.

    NOTE: semantic/vector search over a real documentation knowledge base (spec section 14)
    is a future phase; this only substring-matches the `products` table seeded in Phase 1.
    """
    try:
        if len(query.strip()) < MIN_QUERY_LENGTH:
            return ToolResult(success=False, error="query must not be empty")

        async with get_session() as session:
            products = await product_service.search_products_by_keyword(session, query.strip())
            matches = [
                ProductDocMatchData(product_id=p.id, name=p.name, description=p.description)
                for p in products
            ]
            data = ProductDocSearchData(query=query, matches=matches)
        return ToolResult(success=True, data=data)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in search_product_docs: {exc}")
