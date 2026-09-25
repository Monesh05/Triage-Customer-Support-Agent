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
  "escalation") should investigate. A frustrated tone, high priority, or a routine complaint
  (a duplicate charge, a locked account, an API error) is NOT by itself grounds for
  "escalation" — those are exactly what the specialists exist to investigate; do not add
  "escalation" just because the customer is annoyed. Only include "escalation" when the
  customer explicitly asks to speak to a human, OR the situation is one no automated
  investigation should attempt at all (e.g. a legal threat, a safety/self-harm concern, a
  suspected security breach, fraud, or a request outside anything CloudDesk support can
  address). When you do include "escalation" for a severe/sensitive situation that ALSO
  involves a billing/account/technical/product question, still include the relevant
  specialist(s) too — do not use "escalation" as a way to skip investigation of a legitimate
  question just because the situation is also serious.
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
