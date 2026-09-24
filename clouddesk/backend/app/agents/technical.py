# app/agents/technical.py
# Purpose: Technical Support Agent (spec section 12). Investigates API errors, service
#          availability, usage/rate limits, API key status, and known incidents ONLY — never
#          billing/account tools. Forms a hypothesis and gathers evidence via the bounded
#          tool-call loop (app.agents.base) before producing a TechnicalAgentResult.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from app.agents.base import AgentError, ToolSpec, run_tool_using_agent
from app.agents.schemas import TechnicalAgentResult
from app.tools import product as product_tools
from app.tools import technical as technical_tools
from app.tools.base import ToolResult

logger = logging.getLogger("clouddesk.agents.technical")

AGENT_NAME: str = "technical"

TECHNICAL_SYSTEM_PROMPT: str = """You are the Technical Support Agent for CloudDesk, a B2B SaaS
support system.

You investigate ONLY: API errors, application errors, service availability, usage/rate limits,
API key status, and known incidents. You have no visibility into payments/invoices or account
permissions/login state — do not speculate about them; if the evidence points to an account-side
cause (e.g. entitlement mismatch), say so as a hypothesis for the Account Agent, but do not
investigate account records yourself.

Form a hypothesis and gather supporting evidence BEFORE recommending anything:
1. Check get_recent_incidents / get_service_status first. If there is an active outage matching
   the customer's symptom, that is very likely the cause — do not invent an unrelated
   explanation while an outage is active.
2. Check get_api_key_status to confirm the key is active (not revoked/expired).
3. Check get_api_usage to see if the customer is over their rate limit.
4. search_error_logs and search_product_docs may help but are limited/best-effort.

Every claim in `evidence` must come from actual tool results, never invented. If you could not
gather enough evidence to form a confident hypothesis, set status to "unresolved" or
"needs_escalation" rather than guessing."""


async def _get_api_usage(customer_id: str) -> ToolResult[object]:
    return await technical_tools.get_api_usage(customer_id)


async def _get_api_key_status(customer_id: str) -> ToolResult[object]:
    return await technical_tools.get_api_key_status(customer_id)


async def _get_service_status(service_name: str) -> ToolResult[object]:
    return await technical_tools.get_service_status(service_name)


async def _search_error_logs(query: str) -> ToolResult[object]:
    return await technical_tools.search_error_logs(query)


async def _get_recent_incidents() -> ToolResult[object]:
    return await technical_tools.get_recent_incidents()


async def _search_product_docs(query: str) -> ToolResult[object]:
    return await product_tools.search_product_docs(query)


def _customer_id_params() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {"customer_id": {"type": "string", "description": "Customer UUID"}},
        "required": ["customer_id"],
    }


def _query_params(description: str) -> dict[str, object]:
    return {"type": "object", "properties": {"query": {"type": "string", "description": description}}, "required": ["query"]}


def _build_tools() -> list[ToolSpec]:
    """The exact allow-listed tools for the Technical Agent (spec section 12) — nothing else."""
    cid_params = _customer_id_params()
    return [
        ToolSpec("get_api_usage", "Get the customer's API usage records.", cid_params, _get_api_usage),
        ToolSpec("get_api_key_status", "Get the customer's API key metadata (no secrets).", cid_params, _get_api_key_status),
        ToolSpec(
            "get_service_status",
            "Get the current status of a named service (e.g. 'api', 'auth', 'billing').",
            {"type": "object", "properties": {"service_name": {"type": "string"}}, "required": ["service_name"]},
            _get_service_status,
        ),
        ToolSpec("search_error_logs", "Search application error logs (best-effort).", _query_params("error log query"), _search_error_logs),
        ToolSpec("get_recent_incidents", "List all known service incidents.", {"type": "object", "properties": {}}, _get_recent_incidents),
        ToolSpec("search_product_docs", "Keyword-search product/feature docs.", _query_params("search terms"), _search_product_docs),
    ]


async def run_technical_agent(customer_id: str, customer_message: str) -> TechnicalAgentResult | AgentError:
    """Investigate a technical/API issue using only the allow-listed technical tools."""
    try:
        user_content = f"Customer id: {customer_id}\nCustomer message:\n{customer_message}"
        return await run_tool_using_agent(
            agent_name=AGENT_NAME,
            system_prompt=TECHNICAL_SYSTEM_PROMPT,
            user_content=user_content,
            tools=_build_tools(),
            response_model=TechnicalAgentResult,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("technical_agent_failed customer_id=%s error=%s", customer_id, exc)
        return AgentError(agent=AGENT_NAME, message=f"Technical agent failed: {exc}")
