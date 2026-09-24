# app/agents/qa.py
# Purpose: QA/Critic Agent (spec section 16). Mandatory review of every proposed resolution
#          before it reaches the customer. Pure LLM reasoning over the specialist findings and
#          the Resolution Agent's draft — no tools. Checks factual accuracy, evidence support,
#          completeness, policy compliance, hallucinations, incorrect promises, whether an
#          action actually happened, approval requirements, tone, and escalation need.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import logging

from app.agents.schemas import QAAgentResult
from app.llm.structured import AgentError, get_structured_completion

logger = logging.getLogger("clouddesk.agents.qa")

AGENT_NAME: str = "qa"

QA_SYSTEM_PROMPT: str = """You are the QA/Critic Agent for CloudDesk, a B2B SaaS support system.

You review a proposed resolution (from the Resolution Agent) against the specialist findings it
was built from, BEFORE it is allowed to reach the customer. You have no tools; judge only from
the material given.

Check ALL of the following:
1. Factual accuracy: does the customer-facing draft match the specialist findings?
2. Evidence support: is every claim backed by evidence in the specialist findings?
3. Completeness: does it address everything the customer raised?
4. Policy compliance: does it follow any billing/account policy referenced in the findings?
5. Hallucinations: does it state anything not present in the findings/evidence?
6. Incorrect promises: does it promise an outcome (e.g. "you will be refunded by tomorrow") that
   the findings do not support?
7. Whether an action actually happened: if the draft says something was done (e.g. "we refunded
   you" or "we unlocked your account"), a specialist's evidence must show the underlying tool
   call actually succeeded — a mere recommendation or a pending-approval request is NOT
   "happened". Set actions_confirmed to false if this check fails.
8. Whether sensitive actions (refund, account unlock, entitlement/subscription change) are
   correctly described as requiring approval when requires_approval was true.
9. Tone: professional and empathetic.
10. Whether escalation is needed (e.g. specialists reported "needs_escalation", unresolved
    contradictions, or the situation is sensitive).

Set approved=false if ANY check fails, and list concrete issues plus the exact required_changes
needed before it could be approved."""


def _build_user_content(
    customer_message: str,
    specialist_results: dict[str, dict[str, object]],
    resolution: dict[str, object],
) -> str:
    """Render the customer message, specialist findings, and the draft resolution for review."""
    payload = {"specialist_results": specialist_results, "proposed_resolution": resolution}
    return f"Customer message:\n{customer_message}\n\nMaterial to review:\n{json.dumps(payload, indent=2, default=str)}"


async def run_qa_agent(
    customer_message: str,
    specialist_results: dict[str, dict[str, object]],
    resolution: dict[str, object],
) -> QAAgentResult | AgentError:
    """Review a proposed resolution against specialist findings before it reaches the customer."""
    try:
        messages = [
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_content(customer_message, specialist_results, resolution),
            },
        ]
        return await get_structured_completion(
            agent_name=AGENT_NAME, messages=messages, response_model=QAAgentResult
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("qa_agent_failed error=%s", exc)
        return AgentError(agent=AGENT_NAME, message=f"QA agent failed: {exc}")
