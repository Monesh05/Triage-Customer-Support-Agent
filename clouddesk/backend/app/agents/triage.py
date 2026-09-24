# app/agents/triage.py
# Purpose: Triage Agent (spec section 9). Pure classification of the customer's message: no
#          tools, no attempt to solve the issue. Determines intents, priority, sentiment, which
#          specialist agents are needed, and an obvious-escalation signal via `reason`.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from app.agents.schemas import TriageResult
from app.llm.structured import AgentError, get_structured_completion

logger = logging.getLogger("clouddesk.agents.triage")

AGENT_NAME: str = "triage"

TRIAGE_SYSTEM_PROMPT: str = """You are the Triage Agent for CloudDesk, a B2B SaaS support system.

Your ONLY job is to read the customer's message and classify it. You do NOT investigate
anything, you do NOT have tools, and you must NEVER attempt to solve or explain the issue.

For each message, determine:
- intents: one or more of "billing", "account", "technical", "product", "other" that best
  describe what the customer is reporting or asking about.
- priority: "low", "medium", "high", or "urgent" based on business impact and urgency language.
- sentiment: "frustrated", "angry", "confused", "neutral", or "satisfied".
- required_agents: which specialist agents ("billing", "account", "technical", "product",
  "escalation") should investigate. Include "escalation" only if the customer explicitly asks
  for a human, or the message describes a clearly severe/sensitive situation you cannot
  responsibly leave to automated investigation alone.
- reason: one or two sentences explaining your classification.

Respond only with the structured fields requested. Do not propose a fix, refund, or answer."""


def _build_user_content(customer_message: str, conversation_history: list[str]) -> str:
    """Render the customer message plus any prior turns into a single triage prompt."""
    if not conversation_history:
        return f"Customer message:\n{customer_message}"
    history_block = "\n".join(conversation_history)
    return f"Conversation so far:\n{history_block}\n\nLatest customer message:\n{customer_message}"


async def run_triage_agent(
    customer_message: str, conversation_history: list[str] | None = None
) -> TriageResult | AgentError:
    """Classify a customer message into intents/priority/sentiment/required_agents.

    No tools are used per spec section 9 — this is pure LLM classification.
    """
    try:
        user_content = _build_user_content(customer_message, conversation_history or [])
        messages = [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        return await get_structured_completion(
            agent_name=AGENT_NAME, messages=messages, response_model=TriageResult
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("triage_agent_failed error=%s", exc)
        return AgentError(agent=AGENT_NAME, message=f"Triage agent failed: {exc}")
