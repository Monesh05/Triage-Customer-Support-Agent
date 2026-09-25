# app/graph/routing.py
# Purpose: Pure conditional-edge routing functions for the support StateGraph (spec sections
#          19-22). `route_after_triage` decides which specialist nodes fan out in parallel (or
#          whether to go straight to escalation on an explicit human request). `route_after_qa`
#          implements the bounded reflection loop back to the Resolution Agent. `route_after_finalize`
#          (Phase 5) sends the run to the human-in-the-loop pause node only when approval is
#          actually required. These are plain functions with no side effects so they can be
#          unit-tested without any graph/LLM.
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
    """True if the customer's own words ask for a human — the only case that should skip
    investigation entirely (spec Scenario G). Triage flagging "escalation" is NOT checked here:
    triage may reasonably add "escalation" alongside a real specialist for a merely
    high-priority/frustrated case (its prompt allows this for "severe/sensitive" situations), and
    skipping investigation whenever that happens would mean a normal, fully investigable billing
    complaint never gets looked at by the Billing Agent at all. See `route_after_triage`."""
    message = state.get("customer_message", "").lower()
    return any(keyword in message for keyword in HUMAN_REQUEST_KEYWORDS)


def route_after_triage(state: SupportState) -> list[str]:
    """Decide which specialist node(s) run next, per spec section 20's parallel fan-out.

    Returns a list of node names. `["escalation"]` skips specialists entirely only when the
    customer explicitly asked for a human (in their own words) or triage recognized NO specialist
    at all — including when "escalation" was the ONLY thing triage listed. If triage listed
    "escalation" ALONGSIDE one or more real specialists, the specialists still run first: real
    evidence should inform the handoff, and genuine escalation is still reachable afterwards via
    QA's own `escalation_needed` check or the reflection loop exhausting MAX_ITERATIONS.
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


def route_after_finalize(state: SupportState) -> str:
    """Send the run to the human-in-the-loop pause node (spec section 22) only when
    `finalize_node` determined approval is required; otherwise the run is already complete.
    """
    if state.get("human_approval_required"):
        logger.info("route_after_finalize decision=await_human_decision")
        return "await_human_decision"
    logger.info("route_after_finalize decision=end")
    return "end"
