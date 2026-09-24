# app/graph/resolution_nodes.py
# Purpose: LangGraph node functions for the "back half" of the support StateGraph — resolution,
#          qa, escalation, finalize, and await_human_decision (spec sections 15-17, 19, 22).
#          Split out of app.graph.nodes (which keeps triage + the four specialist nodes) purely to
#          keep each file under this codebase's 300-line-per-file guideline; the two modules
#          share the exact same conventions (never let an exception/AgentError crash the graph,
#          Phase 7 tracing via app.observability.tracer.trace_agent_run for every node that calls
#          an agent). `finalize_node` and `await_human_decision_node` call no agent, so they are
#          not traced.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
from typing import Any

from langgraph.types import interrupt

from app.agents.base import AgentError
from app.agents.escalation import run_escalation_agent
from app.agents.qa import run_qa_agent
from app.agents.resolution import run_resolution_agent
from app.graph.routing import MAX_ITERATIONS
from app.graph.state import SupportState, parse_ticket_uuid
from app.observability.tracer import trace_agent_run

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
APPROVED_ACTION_MESSAGE_SUFFIX: str = " The requested action has been approved and completed."
REJECTED_ACTION_MESSAGE: str = (
    "After review, the requested action was not approved. A member of our team will follow up "
    "with more details."
)


def _prior_qa_feedback(state: SupportState) -> dict[str, Any] | None:
    """The previous iteration's QA rejection reasons, if this is a reflection-loop retry (spec
    section 21). Returns None on the first attempt or once QA has approved, so a fresh run never
    gets stale feedback."""
    qa_result = state.get("qa_result")
    if not qa_result or qa_result.get("approved"):
        return None
    return {
        "issues": qa_result.get("issues", []),
        "required_changes": qa_result.get("required_changes", []),
    }


async def resolution_node(state: SupportState) -> dict[str, Any]:
    """Synthesize specialist findings into a proposed resolution (spec section 15). On any
    iteration after the first, also passes QA's prior rejection reasons back in (spec section 21)
    so the agent fixes what was actually flagged instead of regenerating blind."""
    logger.info("node_enter node=resolution iteration=%d", state.get("iteration", 0))
    next_iteration = state.get("iteration", 0) + 1
    prior_qa_feedback = _prior_qa_feedback(state)
    async with trace_agent_run(
        thread_id=state["thread_id"],
        ticket_id=parse_ticket_uuid(state),
        agent_name="resolution",
        iteration=next_iteration,
    ) as recorder:
        recorder.set_input(state["customer_message"])
        try:
            result = await run_resolution_agent(
                state["customer_message"], state["specialist_results"], prior_qa_feedback
            )
        except Exception as exc:  # noqa: BLE001
            result = AgentError(agent="resolution", message=str(exc))
        if isinstance(result, AgentError):
            recorder.mark_failure(result.message)
            logger.info("node_exit node=resolution status=error")
            return {
                "errors": [f"resolution: {result.message}"],
                "resolution": None,
                "iteration": next_iteration,
                "escalation_required": True,
            }
        recorder.set_output(result)
        logger.info("node_exit node=resolution status=ok iteration=%d", next_iteration)
        return {"resolution": result.model_dump(), "iteration": next_iteration}


async def qa_node(state: SupportState) -> dict[str, Any]:
    """Review the proposed resolution before it can reach the customer (spec section 16)."""
    current_iteration = state.get("iteration", 0)
    logger.info("node_enter node=qa iteration=%d", current_iteration)
    resolution = state.get("resolution") or {}
    async with trace_agent_run(
        thread_id=state["thread_id"],
        ticket_id=parse_ticket_uuid(state),
        agent_name="qa",
        iteration=current_iteration,
    ) as recorder:
        recorder.set_input(state["customer_message"])
        is_final_attempt = current_iteration >= MAX_ITERATIONS
        try:
            result = await run_qa_agent(
                state["customer_message"], state["specialist_results"], resolution, is_final_attempt
            )
        except Exception as exc:  # noqa: BLE001
            result = AgentError(agent="qa", message=str(exc))
        if isinstance(result, AgentError):
            recorder.mark_failure(result.message)
            logger.info("node_exit node=qa status=error")
            return {
                "errors": [f"qa: {result.message}"],
                "qa_result": {"approved": False, "escalation_needed": True},
                "escalation_required": True,
            }
        recorder.set_output(result)
        escalation_required = result.escalation_needed or (not result.approved and is_final_attempt)
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
    async with trace_agent_run(
        thread_id=state["thread_id"], ticket_id=parse_ticket_uuid(state), agent_name="escalation"
    ) as recorder:
        recorder.set_input(state["customer_message"])
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
            recorder.mark_failure(result.message)
            logger.info("node_exit node=escalation status=error")
            return {
                "errors": [f"escalation: {result.message}"],
                "escalation_required": True,
                "final_response": ESCALATION_FALLBACK_MESSAGE,
            }
        recorder.set_output(result)
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
    """QA approved: either flag the run for human approval (spec section 19's Check Actions /
    Approval Required branch) or produce the final customer response directly. This node only
    determines and records WHETHER approval is required; the actual pause happens in the
    following `await_human_decision_node`, once this node's state update has been committed by
    the checkpointer (so a paused run's `human_approval_required`/`pending_actions` are always
    visible to callers, not stuck mid-node).
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


async def await_human_decision_node(state: SupportState) -> dict[str, Any]:
    """Actually pause the graph run (spec section 22) until a human approves or rejects the
    pending actions `finalize_node` recorded. Only reached when `human_approval_required` is
    True. `interrupt()` suspends execution here — `graph.ainvoke` returns to its caller with the
    state as of `finalize_node`'s commit, and this node re-runs from the top on resume, with
    `interrupt()` returning the value passed to `Command(resume=...)`.
    """
    logger.info("node_enter node=await_human_decision thread=%s", state.get("thread_id"))
    pending_actions = state.get("pending_actions", [])
    decision: dict[str, Any] = interrupt({"pending_actions": pending_actions})

    decided = decision.get("actions", [])
    approved = [a for a in decided if a.get("status") == "approved"]
    rejected = [a for a in decided if a.get("status") == "rejected"]

    draft = (state.get("resolution") or {}).get("customer_facing_draft", DEFAULT_RESOLVED_MESSAGE)
    if approved and not rejected:
        final_response = f"{draft}{APPROVED_ACTION_MESSAGE_SUFFIX}"
    elif rejected and not approved:
        final_response = REJECTED_ACTION_MESSAGE
    else:
        final_response = (
            f"{draft} Part of the requested action was approved and completed; the rest was not "
            "approved. A member of our team will follow up with more details."
        )

    logger.info(
        "node_exit node=await_human_decision approved=%d rejected=%d", len(approved), len(rejected)
    )
    # `human_approval_required` has no LangGraph reducer (see app.graph.state.SupportState), so it
    # is overwritten-on-update rather than merged: `finalize_node` sets it True and, without this
    # explicit reset, it would stay True in the final state forever, even after this node resumes
    # and the workflow actually concludes. That was the Phase 5-era bug (spec section 33's DoD):
    # `conversation_service._derive_status` reads this flag first, so a resumed run's status would
    # incorrectly stay "awaiting_approval" instead of correctly reaching "completed"/"escalated".
    return {
        "human_approval_required": False,
        "approved_actions": approved,
        "executed_actions": approved,
        "final_response": final_response,
    }
