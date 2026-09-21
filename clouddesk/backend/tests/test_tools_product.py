# tests/test_tools_product.py
# Purpose: Tests for app.tools.product — search_product_docs (plain keyword search over
#          app.models.product.Product, not semantic/vector search). Uses `committed_session`
#          since this tool opens its own DB connection.
# Author: CloudDesk Team
# Date: 2026-09-21

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.tools import product

_PRODUCT_NAME = "Two-Factor Auth Toolkit"


async def test_search_product_docs_matches_by_keyword(committed_session: AsyncSession) -> None:
    committed_session.add(
        Product(name=_PRODUCT_NAME, description="Enables MFA / two-factor login for accounts.")
    )
    await committed_session.commit()

    try:
        result = await product.search_product_docs("two-factor")

        assert result.success is True
        assert any(match.name == _PRODUCT_NAME for match in result.data.matches)
    finally:
        await committed_session.execute(delete(Product).where(Product.name == _PRODUCT_NAME))
        await committed_session.commit()


async def test_search_product_docs_no_match_returns_empty_list_not_error() -> None:
    result = await product.search_product_docs("zzz_no_such_feature_zzz")

    assert result.success is True
    assert result.data.matches == []


async def test_search_product_docs_rejects_empty_query() -> None:
    result = await product.search_product_docs("   ")

    assert result.success is False
