# app/agents/escalation.py
# Purpose: Escalation Agent (spec section 17). Pure LLM reasoning — no tools. Builds a
#          structured internal handoff for a human agent when the issue cannot be resolved
#          safely/automatically. Never produces a bare "contact support" message.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import logging

from app.agents.schemas import EscalationAgentResult
from app.llm.structured import AgentError, get_structured_completion

logger = logging.getLogger("clouddesk.agents.escalation")

AGENT_NAME: str = "escalation"

ESCALATION_SYSTEM_PROMPT: str = """You are the Escalation Agent for CloudDesk, a B2B SaaS support
system.

You are invoked when an issue cannot be safely resolved automatically: low confidence, a policy
requires a human, a sensitive action needs approval that is unavailable, repeated QA failures,
the customer explicitly asked for a human, or the situation otherwise requires manual review.

Build a structured, USEFUL internal handoff for a human support agent using ONLY the triage
classification and specialist findings given to you. Never simply write "contact support" — the
handoff must let a human pick up the investigation without redoing it: what was found, what
evidence supports it, what was already attempted (including anything still pending approval),
what remains unresolved, and a concrete recommended next action for the human."""


def _build_user_content(
    customer_id: str,
    customer_message: str,
    triage: dict[str, object],
    specialist_results: dict[str, dict[str, object]],
    conversation_history: list[str],
) -> str:
    """Render everything gathered so far as the Escalation Agent's only input."""
    payload = {
        "customer_id": customer_id,
        "customer_message": customer_message,
        "triage": triage,
        "specialist_results": specialist_results,
        "conversation_history": conversation_history,
    }
    return f"Escalation context:\n{json.dumps(payload, indent=2, default=str)}"


async def run_escalation_agent(
    customer_id: str,
    customer_message: str,
    triage: dict[str, object],
    specialist_results: dict[str, dict[str, object]],
    conversation_history: list[str] | None = None,
) -> EscalationAgentResult | AgentError:
    """Build a structured human-escalation handoff from the triage/specialist findings so far."""
    try:
        history = conversation_history or []
        messages = [
            {"role": "system", "content": ESCALATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_content(
                    customer_id, customer_message, triage, specialist_results, history
                ),
            },
        ]
        return await get_structured_completion(
            agent_name=AGENT_NAME, messages=messages, response_model=EscalationAgentResult
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("escalation_agent_failed customer_id=%s error=%s", customer_id, exc)
        return AgentError(agent=AGENT_NAME, message=f"Escalation agent failed: {exc}")
