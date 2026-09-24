# app/agents/resolution.py
# Purpose: Resolution Agent (spec section 15). Pure LLM reasoning over prior specialist agents'
#          structured outputs — no tools. Synthesizes findings, flags contradictions/unresolved
#          issues, and drafts a customer-facing response. Must NOT independently invent facts:
#          only the specialist findings passed in are given as context.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import logging

from app.agents.schemas import ResolutionAgentResult
from app.llm.structured import AgentError, get_structured_completion

logger = logging.getLogger("clouddesk.agents.resolution")

AGENT_NAME: str = "resolution"

RESOLUTION_SYSTEM_PROMPT: str = """You are the Resolution Agent for CloudDesk, a B2B SaaS support
system.

You receive the structured findings of one or more specialist agents (Billing, Account,
Technical, Product) for a single customer message. Your job:

- Synthesize their findings into a coherent picture.
- Identify contradictions between specialists, if any.
- Clearly distinguish established FACTS (from specialist findings/evidence) from RECOMMENDATIONS
  (proposed actions that still require approval or execution).
- Identify unresolved questions the specialists could not answer.
- Construct a proposed resolution describing what should happen next.
- Write a customer-facing draft response in a clear, empathetic, professional tone.

CRITICAL: You must NOT invent facts, evidence, or outcomes that are not present in the specialist
findings given to you. If a specialist's status was "unresolved" or "needs_escalation", reflect
that honestly rather than papering over it. Never claim in the customer-facing draft that an
action (e.g. a refund) has been completed unless a specialist's evidence explicitly shows it
succeeded — a "recommended_actions" entry with requires_approval=true is NOT a completed action;
describe it as pending approval."""


def _build_user_content(customer_message: str, specialist_results: dict[str, dict[str, object]]) -> str:
    """Render the customer message and specialist findings as the Resolution Agent's only input."""
    findings_json = json.dumps(specialist_results, indent=2, default=str)
    return (
        f"Customer message:\n{customer_message}\n\n"
        f"Specialist agent findings (the ONLY facts/recommendations you may use):\n{findings_json}"
    )


async def run_resolution_agent(
    customer_message: str, specialist_results: dict[str, dict[str, object]]
) -> ResolutionAgentResult | AgentError:
    """Synthesize specialist findings into a proposed resolution and customer-facing draft."""
    try:
        messages = [
            {"role": "system", "content": RESOLUTION_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_content(customer_message, specialist_results)},
        ]
        return await get_structured_completion(
            agent_name=AGENT_NAME, messages=messages, response_model=ResolutionAgentResult
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("resolution_agent_failed error=%s", exc)
        return AgentError(agent=AGENT_NAME, message=f"Resolution agent failed: {exc}")
