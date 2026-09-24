# app/agents/product.py
# Purpose: Product Agent (spec section 13). Answers product/documentation questions using ONLY
#          search_product_docs, now backed by real pgvector semantic search over the Phase 6
#          Product RAG knowledge base (spec section 14) instead of the earlier keyword stub.
#          Must cite only what was actually retrieved and never invent doc content; the tool
#          itself enforces a minimum-similarity floor, so an empty `matches` list here means
#          "genuinely not found," not "search failed to look hard enough."
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

You have exactly one tool: search_product_docs. It performs a real semantic search over
CloudDesk's product knowledge base (product documentation, pricing, API documentation,
troubleshooting guides, billing/refund policy, account recovery, and feature documentation),
optionally filtered by `category` or `product`. It already applies a minimum-relevance
threshold, so if it returns no matches, that means nothing relevant genuinely exists in the
knowledge base — not that you should try to answer from general knowledge instead.

Call search_product_docs with a natural-language version of the question before answering.
Your answer must be grounded ONLY in what the tool actually returned:
- If it returns matches, answer using their `chunk_text` and cite each one in `sources` using
  its `document_id`, `title`, and `category` exactly as returned. Set `grounded` to true.
- If it returns no matches (or the tool call fails), say plainly that you could not find
  documentation on this in the current knowledge base — do NOT invent product details. Set
  `grounded` to false and leave `sources` empty."""


async def _search_product_docs(
    query: str, category: str | None = None, product: str | None = None
) -> ToolResult[object]:
    return await product_tools.search_product_docs(query, category=category, product=product)


def _build_tools() -> list[ToolSpec]:
    """The exact allow-listed tool for the Product Agent (spec section 13) — nothing else."""
    return [
        ToolSpec(
            name="search_product_docs",
            description=(
                "Semantically search CloudDesk's product knowledge base (docs, pricing, API, "
                "troubleshooting, billing/refund policy, account recovery, feature docs)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language search query"},
                    "category": {
                        "type": "string",
                        "description": (
                            "Optional exact category filter, e.g. 'pricing', 'troubleshooting', "
                            "'refund policy'."
                        ),
                    },
                    "product": {
                        "type": "string",
                        "description": "Optional exact product filter, e.g. 'CloudDesk API'.",
                    },
                },
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
