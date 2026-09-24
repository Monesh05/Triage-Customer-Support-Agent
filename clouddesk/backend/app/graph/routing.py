# app/graph/routing.py
# Purpose: Pure conditional-edge routing functions for the support StateGraph (spec sections
#          19-21). `route_after_triage` decides which specialist nodes fan out in parallel (or
#          whether to go straight to escalation on an explicit human request). `route_after_qa`
#          implements the bounded reflection loop back to the Resolution Agent. These are plain
#          functions with no side effects so they can be unit-tested without any graph/LLM.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from app.graph.state import SupportState

logger = logging.getLogger("clouddesk.graph.routing")

MAX_ITERATIONS: int = 3

SPECIALIST_AGENT_NAMES: frozenset[str] = frozenset({"billing", "account", "technical", "product"})

# Backup safety net (spec Scenario G): explicit human-request phrases in the customer's own
# words, in case the Triage Agent's `required_agents` did not already flag "escalation".
HUMAN_REQUEST_KEYWORDS: tuple[str, ...] = (
    "speak to a human",
    "talk to a human",
    "speak to a person",
    "talk to a person",
    "human agent",
    "real person",
    "human representative",
    "speak with a representative",
)


def _explicit_human_request(state: SupportState) -> bool:
    """True if triage flagged escalation directly, or the raw message asks for a human."""
    if "escalation" in state.get("required_agents", []):
        return True
    message = state.get("customer_message", "").lower()
    return any(keyword in message for keyword in HUMAN_REQUEST_KEYWORDS)


def route_after_triage(state: SupportState) -> list[str]:
    """Decide which specialist node(s) run next, per spec section 20's parallel fan-out.

    Returns a list of node names. `["escalation"]` skips specialists entirely (explicit human
    request or a severe/sensitive signal from triage). An empty `required_agents` with no
    recognizable specialist also falls back to escalation rather than silently doing nothing.
    """
    if _explicit_human_request(state):
        logger.info("route_after_triage decision=escalation reason=explicit_human_request")
        return ["escalation"]

    specialists = [agent for agent in state.get("required_agents", []) if agent in SPECIALIST_AGENT_NAMES]
    if not specialists:
        logger.info("route_after_triage decision=escalation reason=no_recognized_specialist")
        return ["escalation"]

    logger.info("route_after_triage decision=%s", specialists)
    return specialists


def route_after_qa(state: SupportState) -> str:
    """Implements the reflection loop (spec section 21): approved -> finalize, not yet at
    MAX_ITERATIONS -> back to resolution, otherwise -> escalation to prevent infinite loops.
    """
    qa_result = state.get("qa_result")
    approved = bool(qa_result and qa_result.get("approved"))
    iteration = state.get("iteration", 0)

    if approved:
        logger.info("route_after_qa decision=finalize iteration=%d", iteration)
        return "finalize"
    if iteration < MAX_ITERATIONS:
        logger.info("route_after_qa decision=resolution iteration=%d", iteration)
        return "resolution"
    logger.info("route_after_qa decision=escalation iteration=%d (max reached)", iteration)
    return "escalation"
