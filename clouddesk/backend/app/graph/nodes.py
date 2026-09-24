# app/graph/nodes.py
# Purpose: LangGraph node functions for the support StateGraph (spec sections 19-22). Each node
#          wraps exactly one Phase 3 agent call, translating its `SchemaT | AgentError` result
#          into a partial SupportState update. No node ever lets an exception or AgentError
#          propagate/crash the graph — failures degrade to an `errors` entry and a safe fallback
#          (usually routing toward escalation) instead.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
from typing import Any

from app.agents.account import run_account_agent
from app.agents.base import AgentError
from app.agents.billing import run_billing_agent
from app.agents.escalation import run_escalation_agent
from app.agents.product import run_product_agent
from app.agents.qa import run_qa_agent
from app.agents.resolution import run_resolution_agent
from app.agents.technical import run_technical_agent
from app.agents.triage import run_triage_agent
from app.graph.routing import MAX_ITERATIONS
from app.graph.state import SupportState

logger = logging.getLogger("clouddesk.graph.nodes")

ESCALATION_FALLBACK_MESSAGE: str = (
    "Your issue has been escalated to a human specialist who will review the full details of "
    "your case and follow up with you directly."
)
APPROVAL_PENDING_MESSAGE_SUFFIX: str = (
    " This includes an action that requires internal approval before it can be completed; "
    "you will be notified once it is reviewed."
)
DEFAULT_RESOLVED_MESSAGE: str = "Your issue has been reviewed and resolved."


async def triage_node(state: SupportState) -> dict[str, Any]:
    """Classify the customer message (spec section 9). No tools; pure classification."""
    logger.info("node_enter node=triage")
    try:
        result = await run_triage_agent(state["customer_message"], state["conversation_history"])
    except Exception as exc:  # noqa: BLE001
        result = AgentError(agent="triage", message=str(exc))
    if isinstance(result, AgentError):
        logger.info("node_exit node=triage status=error")
        return {
            "errors": [f"triage: {result.message}"],
            "intents": ["other"],
            "priority": "high",
            "sentiment": "neutral",
            "required_agents": ["escalation"],
        }
    logger.info("node_exit node=triage status=ok required_agents=%s", result.required_agents)
    return {
        "intents": list(result.intents),
        "priority": result.priority,
        "sentiment": result.sentiment,
        "required_agents": list(result.required_agents),
    }


async def _run_specialist(
    node_name: str, coroutine: Any
) -> dict[str, Any]:
    """Shared wrapper: run one specialist agent call, store its result/error under its own key."""
    logger.info("node_enter node=%s", node_name)
    try:
        result = await coroutine
    except Exception as exc:  # noqa: BLE001
        result = AgentError(agent=node_name, message=str(exc))
    if isinstance(result, AgentError):
        logger.info("node_exit node=%s status=error", node_name)
        return {
            "errors": [f"{node_name}: {result.message}"],
            "specialist_results": {node_name: {"error": result.message}},
        }
    logger.info("node_exit node=%s status=ok", node_name)
    return {"specialist_results": {node_name: result.model_dump()}}


async def billing_node(state: SupportState) -> dict[str, Any]:
    """Investigate billing (spec section 10). Runs only when routed by route_after_triage."""
    return await _run_specialist(
        "billing", run_billing_agent(state["customer_id"], state["customer_message"])
    )


async def account_node(state: SupportState) -> dict[str, Any]:
    """Investigate account/access/entitlements (spec section 11)."""
    return await _run_specialist(
        "account", run_account_agent(state["customer_id"], state["customer_message"])
    )


async def technical_node(state: SupportState) -> dict[str, Any]:
    """Investigate API/technical issues (spec section 12)."""
    return await _run_specialist(
        "technical", run_technical_agent(state["customer_id"], state["customer_message"])
    )


async def product_node(state: SupportState) -> dict[str, Any]:
    """Answer product/documentation questions (spec section 13)."""
    return await _run_specialist("product", run_product_agent(state["customer_message"]))


async def resolution_node(state: SupportState) -> dict[str, Any]:
    """Synthesize specialist findings into a proposed resolution (spec section 15)."""
    logger.info("node_enter node=resolution iteration=%d", state.get("iteration", 0))
    next_iteration = state.get("iteration", 0) + 1
    try:
        result = await run_resolution_agent(state["customer_message"], state["specialist_results"])
    except Exception as exc:  # noqa: BLE001
        result = AgentError(agent="resolution", message=str(exc))
    if isinstance(result, AgentError):
        logger.info("node_exit node=resolution status=error")
        return {
            "errors": [f"resolution: {result.message}"],
            "resolution": None,
            "iteration": next_iteration,
            "escalation_required": True,
        }
    logger.info("node_exit node=resolution status=ok iteration=%d", next_iteration)
    return {"resolution": result.model_dump(), "iteration": next_iteration}


async def qa_node(state: SupportState) -> dict[str, Any]:
    """Review the proposed resolution before it can reach the customer (spec section 16)."""
    logger.info("node_enter node=qa iteration=%d", state.get("iteration", 0))
    resolution = state.get("resolution") or {}
    try:
        result = await run_qa_agent(state["customer_message"], state["specialist_results"], resolution)
    except Exception as exc:  # noqa: BLE001
        result = AgentError(agent="qa", message=str(exc))
    if isinstance(result, AgentError):
        logger.info("node_exit node=qa status=error")
        return {
            "errors": [f"qa: {result.message}"],
            "qa_result": {"approved": False, "escalation_needed": True},
            "escalation_required": True,
        }
    at_max_iterations = state.get("iteration", 0) >= MAX_ITERATIONS
    escalation_required = result.escalation_needed or (not result.approved and at_max_iterations)
    logger.info("node_exit node=qa status=ok approved=%s", result.approved)
    return {"qa_result": result.model_dump(), "escalation_required": escalation_required}


def _build_triage_summary(state: SupportState) -> dict[str, Any]:
    """The triage classification subset the Escalation Agent needs (spec section 17)."""
    return {
        "intents": state.get("intents", []),
        "priority": state.get("priority", "medium"),
        "sentiment": state.get("sentiment", "neutral"),
        "required_agents": state.get("required_agents", []),
    }


async def escalation_node(state: SupportState) -> dict[str, Any]:
    """Build a structured human handoff (spec section 17) and a safe customer-facing message."""
    logger.info("node_enter node=escalation")
    try:
        result = await run_escalation_agent(
            state["customer_id"],
            state["customer_message"],
            _build_triage_summary(state),
            state["specialist_results"],
            state.get("conversation_history"),
        )
    except Exception as exc:  # noqa: BLE001
        result = AgentError(agent="escalation", message=str(exc))
    if isinstance(result, AgentError):
        logger.info("node_exit node=escalation status=error")
        return {
            "errors": [f"escalation: {result.message}"],
            "escalation_required": True,
            "final_response": ESCALATION_FALLBACK_MESSAGE,
        }
    logger.info("node_exit node=escalation status=ok")
    return {
        "escalation_result": result.model_dump(),
        "escalation_required": True,
        "final_response": ESCALATION_FALLBACK_MESSAGE,
    }


def _collect_pending_actions(specialist_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Gather every specialist-recommended action that requires human approval (spec section 22)."""
    pending: list[dict[str, Any]] = []
    for agent_name, agent_result in specialist_results.items():
        for action in agent_result.get("recommended_actions") or []:
            if action.get("requires_approval"):
                pending.append({"agent": agent_name, **action})
    return pending


async def finalize_node(state: SupportState) -> dict[str, Any]:
    """QA approved: either hold for human approval or produce the final customer response
    (spec section 19's Check Actions / Approval Required branch, minus execution — Phase 5).
    """
    logger.info("node_enter node=finalize")
    resolution = state.get("resolution") or {}
    pending_actions = _collect_pending_actions(state.get("specialist_results", {}))
    requires_approval = bool(resolution.get("requires_approval")) or bool(pending_actions)

    if requires_approval:
        draft = resolution.get("customer_facing_draft", DEFAULT_RESOLVED_MESSAGE)
        logger.info("node_exit node=finalize status=approval_required actions=%d", len(pending_actions))
        return {
            "human_approval_required": True,
            "pending_actions": pending_actions,
            "final_response": f"{draft}{APPROVAL_PENDING_MESSAGE_SUFFIX}",
        }

    logger.info("node_exit node=finalize status=resolved")
    return {"final_response": resolution.get("customer_facing_draft", DEFAULT_RESOLVED_MESSAGE)}
