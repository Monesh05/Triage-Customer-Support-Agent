# app/agents/product.py
# Purpose: Product Agent (spec section 13). Answers product/documentation questions using ONLY
#          search_product_docs (spec section 14 notes real pgvector RAG is a later phase; this
#          keyword search over app.models.product.Product is the only grounding available now).
#          Must cite only what was actually retrieved and never invent doc content.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from app.agents.base import AgentError, ToolSpec, run_tool_using_agent
from app.agents.schemas import ProductAgentResult
from app.tools import product as product_tools
from app.tools.base import ToolResult

logger = logging.getLogger("clouddesk.agents.product")

AGENT_NAME: str = "product"

PRODUCT_SYSTEM_PROMPT: str = """You are the Product Agent for CloudDesk, a B2B SaaS support system.

You answer ONLY product/documentation questions (features, pricing tiers, how something works,
how to do something). You have no visibility into a specific customer's billing, account, or
technical state — do not speculate about their individual situation.

You have exactly one tool: search_product_docs. This is a keyword search over CloudDesk's
current product/feature catalog — it is NOT a full documentation corpus (a real semantic search
over a full knowledge base is a future capability, not available to you now).

Call search_product_docs with relevant keywords from the question before answering. Your answer
must be grounded ONLY in what the tool actually returned:
- If it returns relevant matches, answer using those matches and list them in `sources`, set
  `grounded` to true.
- If it returns no matches (or the tool call fails), say plainly that you could not find
  documentation on this in the current catalog — do NOT invent product details. Set `grounded`
  to false and leave `sources` empty."""


async def _search_product_docs(query: str) -> ToolResult[object]:
    return await product_tools.search_product_docs(query)


def _build_tools() -> list[ToolSpec]:
    """The exact allow-listed tool for the Product Agent (spec section 13) — nothing else."""
    return [
        ToolSpec(
            name="search_product_docs",
            description="Keyword-search CloudDesk's current product/feature catalog.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search keywords"}},
                "required": ["query"],
            },
            handler=_search_product_docs,
        )
    ]


async def run_product_agent(customer_message: str) -> ProductAgentResult | AgentError:
    """Answer a product/documentation question using only search_product_docs."""
    try:
        return await run_tool_using_agent(
            agent_name=AGENT_NAME,
            system_prompt=PRODUCT_SYSTEM_PROMPT,
            user_content=f"Customer question:\n{customer_message}",
            tools=_build_tools(),
            response_model=ProductAgentResult,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("product_agent_failed error=%s", exc)
        return AgentError(agent=AGENT_NAME, message=f"Product agent failed: {exc}")
