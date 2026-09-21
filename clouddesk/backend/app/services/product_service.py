# app/services/product_service.py
# Purpose: Business logic for product/feature lookup. Backs the Phase 2 `search_product_docs`
#          tool with a simple keyword (ILIKE) search over the `products` table's real text
#          fields. This is NOT the pgvector semantic-search RAG pipeline described in spec
#          section 14 — that is a later phase; this is a plain substring search over existing
#          Phase 1 data so the tool layer never fabricates results.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

logger = logging.getLogger(__name__)

MAX_PRODUCT_SEARCH_RESULTS: int = 10


async def search_products_by_keyword(session: AsyncSession, query: str) -> list[Product]:
    """Case-insensitive substring search over product name/description.

    Returns at most `MAX_PRODUCT_SEARCH_RESULTS` matches, ordered by name. Returns an
    empty list (never raises NotFoundError) when nothing matches, since "no docs found"
    is a normal, valid outcome for a search.
    """
    pattern = f"%{query}%"
    result = await session.execute(
        select(Product)
        .where(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))
        .order_by(Product.name)
        .limit(MAX_PRODUCT_SEARCH_RESULTS)
    )
    return list(result.scalars().all())
