# tests/test_graph_live_integration.py
# Purpose: ONE real end-to-end proof that the compiled support StateGraph works against the
#          configured LLM provider (per .env) AND the real database (Scenario A, spec section 23
#          - a simple product FAQ). Marked `integration` and excluded from the default `pytest`
#          run (see pytest.ini addopts), same policy as tests/test_agents_live_integration.py.
#          Run explicitly with:
#              pytest -m integration tests/test_graph_live_integration.py -v -s
# Author: CloudDesk Team
# Date: 2026-09-24

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.graph import run_support_workflow
from app.models.product import Product

pytestmark = pytest.mark.integration

_PRODUCT_NAME = "Pro Plan API Access"


async def test_support_workflow_live_simple_faq(committed_session: AsyncSession) -> None:
    """Scenario A end-to-end: triage -> product -> resolution -> qa -> finalize, for real."""
    committed_session.add(
        Product(
            name=_PRODUCT_NAME,
            description="The Pro plan includes full API access with a 100,000 requests/month limit.",
        )
    )
    await committed_session.commit()

    try:
        final_state = await run_support_workflow(
            customer_id="00000000-0000-0000-0000-000000000000",
            customer_message="Does the Pro plan include API access?",
        )

        print("\n--- LIVE GRAPH RUN: FINAL STATE ---")
        for key, value in final_state.items():
            print(f"{key}: {value}")

        assert final_state["required_agents"]
        assert "product" in final_state["specialist_results"]
        assert final_state["final_response"]
        assert not final_state["errors"]
    finally:
        await committed_session.execute(delete(Product).where(Product.name == _PRODUCT_NAME))
        await committed_session.commit()
