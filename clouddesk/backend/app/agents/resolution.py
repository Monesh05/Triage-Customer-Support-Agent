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
describe it as pending approval.

REVISING AFTER QA FEEDBACK: If a "Prior QA feedback" section is present in the user message, the
QA/Critic Agent has already REJECTED your previous draft for the reasons and required changes
listed there. You MUST treat that feedback as binding: address every single item in
`required_changes` explicitly in this new draft, and do not simply regenerate a similar response
from scratch and hope it happens to pass. Keep whatever parts of your prior synthesis were not
criticized, and change only what QA flagged. If you are unsure how to satisfy a required change
without contradicting the specialist findings, say so honestly in `unresolved_questions` rather
than repeating the rejected wording or inventing a new unsupported claim."""


def _build_user_content(
    customer_message: str,
    specialist_results: dict[str, dict[str, object]],
    prior_qa_feedback: dict[str, object] | None,
) -> str:
    """Render the customer message, specialist findings, and any prior QA rejection reasons as
    the Resolution Agent's input. `prior_qa_feedback` is only present on retry iterations (spec
    section 21's reflection loop) and carries the previous `QAAgentResult.issues` and
    `required_changes` so the agent can actually fix what QA rejected, instead of regenerating a
    similar draft blind."""
    findings_json = json.dumps(specialist_results, indent=2, default=str)
    sections = [
        f"Customer message:\n{customer_message}",
        f"Specialist agent findings (the ONLY facts/recommendations you may use):\n{findings_json}",
    ]
    if prior_qa_feedback:
        feedback_json = json.dumps(prior_qa_feedback, indent=2, default=str)
        sections.append(
            "Prior QA feedback (your last draft was REJECTED for these reasons — you MUST "
            f"address every item in required_changes below):\n{feedback_json}"
        )
    return "\n\n".join(sections)


async def run_resolution_agent(
    customer_message: str,
    specialist_results: dict[str, dict[str, object]],
    prior_qa_feedback: dict[str, object] | None = None,
) -> ResolutionAgentResult | AgentError:
    """Synthesize specialist findings into a proposed resolution and customer-facing draft.

    `prior_qa_feedback` (spec section 21), when given, is the previous iteration's
    `QAAgentResult` (as a dict, at minimum `issues`/`required_changes`) so a retry after a QA
    rejection can actually converge instead of regenerating a similarly-flawed draft blind.
    """
    try:
        messages = [
            {"role": "system", "content": RESOLUTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_content(customer_message, specialist_results, prior_qa_feedback),
            },
        ]
        return await get_structured_completion(
            agent_name=AGENT_NAME, messages=messages, response_model=ResolutionAgentResult
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("resolution_agent_failed error=%s", exc)
        return AgentError(agent=AGENT_NAME, message=f"Resolution agent failed: {exc}")
