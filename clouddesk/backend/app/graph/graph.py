# app/graph/graph.py
# Purpose: Assembles and compiles the support StateGraph (spec sections 3, 18-22):
#          START -> triage -> [parallel specialist fan-out OR straight to escalation]
#                -> resolution -> qa -> [back to resolution | escalation | finalize] -> END,
#          with finalize -> await_human_decision -> END added in Phase 5 whenever human approval
#          is required. The graph is compiled WITH a checkpointer (spec section 22: "use LangGraph
#          interruption/checkpoint mechanisms") so `await_human_decision_node`'s `interrupt()`
#          call actually pauses a run rather than merely reporting "approval needed" after fully
#          finishing. `run_support_workflow` starts a new run (and pending actions arising from it
#          are persisted via app.services.approval_service, and a `support_tickets` row is
#          best-effort auto-created up front per Phase 7 — see `_create_ticket_if_possible` —
#          since a trace with no ticket to hang off of is much less useful, spec sections 7/26);
#          `resume_support_workflow` continues a previously paused run once a human decision has
#          been recorded for every one of its pending actions.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app.database.session import get_session
from app.graph import nodes, resolution_nodes
from app.graph.routing import route_after_finalize, route_after_qa, route_after_triage
from app.graph.state import SupportState, build_initial_state
from app.models.enums import TicketPriority
from app.services import approval_service, ticket_service
from app.services.exceptions import InvalidStateError

logger = logging.getLogger("clouddesk.graph")

TICKET_SUBJECT_MAX_LENGTH: int = 117  # Column is String(255); leaves room for an added "...".
WORKFLOW_TICKET_ACTOR: str = "system:support_workflow"

SPECIALIST_NODES: tuple[str, ...] = ("billing", "account", "technical", "product")

# Phase 5 uses an in-process checkpointer (spec section 22). A single backend process keeps every
# paused thread's state in memory for the lifetime of the process, which is sufficient for this
# phase's scope (interrupt/resume mechanics + the approval API) and for tests. It does NOT survive
# a process restart — `langgraph-checkpoint-postgres` is not an installed dependency yet, and
# adding it (plus the CVE/version-pinning check every new dependency requires) is left as a
# Phase 10 (production hardening) follow-up rather than done ad hoc here.
_CHECKPOINTER = MemorySaver()


def _register_nodes(graph: StateGraph[SupportState]) -> None:
    graph.add_node("triage", nodes.triage_node)
    graph.add_node("billing", nodes.billing_node)
    graph.add_node("account", nodes.account_node)
    graph.add_node("technical", nodes.technical_node)
    graph.add_node("product", nodes.product_node)
    graph.add_node("resolution", resolution_nodes.resolution_node)
    graph.add_node("qa", resolution_nodes.qa_node)
    graph.add_node("escalation", resolution_nodes.escalation_node)
    graph.add_node("finalize", resolution_nodes.finalize_node)
    graph.add_node("await_human_decision", resolution_nodes.await_human_decision_node)


def _wire_edges(graph: StateGraph[SupportState]) -> None:
    graph.add_edge(START, "triage")

    # Dynamic router (spec section 20): fans out into 1-4 specialist nodes running in parallel,
    # or routes straight to escalation on an explicit human request / unrecognized intent.
    # Whichever specialists run all converge on "resolution" (automatic fan-in).
    triage_path_map = {name: name for name in (*SPECIALIST_NODES, "escalation")}
    graph.add_conditional_edges("triage", route_after_triage, triage_path_map)
    for specialist in SPECIALIST_NODES:
        graph.add_edge(specialist, "resolution")
    graph.add_edge("resolution", "qa")

    # Reflection loop (spec section 21): bounded return to "resolution" before escalation.
    graph.add_conditional_edges(
        "qa", route_after_qa, {"resolution": "resolution", "escalation": "escalation", "finalize": "finalize"}
    )

    # Human-in-the-loop (spec section 22): finalize only decides whether approval is required;
    # the pause itself happens in await_human_decision (see that node's docstring for why).
    graph.add_conditional_edges(
        "finalize", route_after_finalize, {"await_human_decision": "await_human_decision", "end": END}
    )
    graph.add_edge("escalation", END)
    graph.add_edge("await_human_decision", END)


def build_support_graph() -> CompiledStateGraph:
    """Build and compile the support StateGraph. See module docstring for the topology."""
    graph: StateGraph[SupportState] = StateGraph(SupportState)
    _register_nodes(graph)
    _wire_edges(graph)
    return graph.compile(checkpointer=_CHECKPOINTER)


_compiled_graph: CompiledStateGraph | None = None


def get_support_graph() -> CompiledStateGraph:
    """Return the compiled support graph, building it once and reusing it thereafter."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_support_graph()
    return _compiled_graph


def _thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


async def _persist_pending_actions(customer_id: str, thread_id: str, state: SupportState) -> None:
    """Create one persistent ApprovalRequest row (app.services.approval_service) per pending
    action a paused run just surfaced, so the approval API/UI has something to list and decide on.
    """
    pending_actions = state.get("pending_actions", [])
    if not pending_actions:
        return
    try:
        customer_uuid = uuid.UUID(customer_id)
    except ValueError:
        # customer_id isn't a real customer record id (e.g. a mocked-agent test double) — the
        # paused state is still returned to the caller with human_approval_required/pending_actions
        # set; only the persistent approval-queue bookkeeping is skipped, same as any other
        # non-fatal side effect in this workflow (spec section 27: never crash on a side channel).
        logger.warning("skip_persist_pending_actions reason=invalid_customer_id thread_id=%s", thread_id)
        return

    async with get_session() as session:
        for action in pending_actions:
            agent_name = str(action.get("agent", "unknown"))
            await approval_service.create_pending_action(
                session, customer_uuid, thread_id, agent_name, action
            )


def _derive_ticket_subject(customer_message: str) -> str:
    """A short ticket subject line from the raw customer message (spec section 5's `subject`
    is a required, length-bounded field; the full message is kept verbatim as `description`)."""
    stripped = customer_message.strip() or "Support request"
    if len(stripped) <= TICKET_SUBJECT_MAX_LENGTH:
        return stripped
    return stripped[:TICKET_SUBJECT_MAX_LENGTH].rstrip() + "..."


async def _create_ticket_if_possible(customer_id: str, customer_message: str) -> str | None:
    """Best-effort auto-create a `SupportTicket` for this workflow run (Phase 7, spec sections
    7/24/26: tickets are the top-level object a trace hangs off of, and none was ever created for
    a support-workflow run before this phase). Mirrors `_persist_pending_actions`'s non-fatal
    handling of a non-UUID/unknown customer id: this bookkeeping must never block or crash the
    actual support workflow, so any failure here just means `ticket_id` stays `None`.
    """
    try:
        customer_uuid = uuid.UUID(customer_id)
    except ValueError:
        logger.warning("skip_ticket_autocreate reason=invalid_customer_id")
        return None
    try:
        async with get_session() as session:
            ticket = await ticket_service.create_ticket(
                session,
                customer_uuid,
                subject=_derive_ticket_subject(customer_message),
                description=customer_message,
                priority=TicketPriority.MEDIUM,
                actor=WORKFLOW_TICKET_ACTOR,
            )
            return str(ticket.id)
    except Exception:  # noqa: BLE001 - see docstring: never block the workflow on this
        logger.exception("ticket_autocreate_failed customer_id=%s", customer_id)
        return None


async def run_support_workflow(
    customer_id: str,
    customer_message: str,
    conversation_history: list[str] | None = None,
) -> SupportState:
    """Build the initial state and run the support workflow, returning the final (or paused)
    state. When the run pauses for human approval, `final_state["human_approval_required"]` is
    True, `final_state["thread_id"]` identifies the paused run, and a persistent approval-queue
    row has already been created for each pending action (spec section 22).
    """
    logger.info("support_workflow_start customer_id=%s", customer_id)
    ticket_id = await _create_ticket_if_possible(customer_id, customer_message)
    initial_state = build_initial_state(customer_id, customer_message, conversation_history, ticket_id=ticket_id)
    thread_id = initial_state["thread_id"]
    graph = get_support_graph()
    final_state: SupportState = await graph.ainvoke(initial_state, config=_thread_config(thread_id))

    if final_state.get("human_approval_required") and final_state.get("pending_actions"):
        await _persist_pending_actions(customer_id, thread_id, final_state)

    logger.info(
        "support_workflow_end customer_id=%s thread_id=%s escalation_required=%s human_approval_required=%s",
        customer_id, thread_id, final_state.get("escalation_required"), final_state.get("human_approval_required"),
    )
    return final_state


async def resume_support_workflow(thread_id: str, decision: dict[str, Any]) -> SupportState:
    """Resume a previously paused run once a human decision is available for its pending actions.

    `decision` is `{"actions": [{"action_id": str, "status": "approved"|"rejected", ...}, ...]}`,
    matching every entry the paused state's `pending_actions` produced (see
    app.graph.resolution_nodes.await_human_decision_node).

    Raises:
        InvalidStateError: if `thread_id` has no run currently paused waiting on a decision.
    """
    graph = get_support_graph()
    config = _thread_config(thread_id)

    snapshot = await graph.aget_state(config)
    if not snapshot or not snapshot.next:
        raise InvalidStateError(f"No paused workflow run found for thread {thread_id}")

    logger.info("support_workflow_resume thread_id=%s", thread_id)
    final_state: SupportState = await graph.ainvoke(Command(resume=decision), config=config)
    logger.info(
        "support_workflow_resumed thread_id=%s final_response_set=%s",
        thread_id, bool(final_state.get("final_response")),
    )
    return final_state
