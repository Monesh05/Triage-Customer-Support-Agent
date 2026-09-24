# app/graph/graph.py
# Purpose: Assembles and compiles the support StateGraph (spec sections 3, 18-21):
#          START -> triage -> [parallel specialist fan-out OR straight to escalation]
#                -> resolution -> qa -> [back to resolution | escalation | finalize] -> END.
#          Exposes `run_support_workflow` as the single entrypoint that builds the initial
#          state and invokes the compiled graph. The compiled graph is built once and reused.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph import nodes
from app.graph.routing import route_after_qa, route_after_triage
from app.graph.state import SupportState, build_initial_state

logger = logging.getLogger("clouddesk.graph")

SPECIALIST_NODES: tuple[str, ...] = ("billing", "account", "technical", "product")


def build_support_graph() -> CompiledStateGraph:
    """Build and compile the support StateGraph. See module docstring for the topology."""
    graph: StateGraph[SupportState] = StateGraph(SupportState)

    graph.add_node("triage", nodes.triage_node)
    graph.add_node("billing", nodes.billing_node)
    graph.add_node("account", nodes.account_node)
    graph.add_node("technical", nodes.technical_node)
    graph.add_node("product", nodes.product_node)
    graph.add_node("resolution", nodes.resolution_node)
    graph.add_node("qa", nodes.qa_node)
    graph.add_node("escalation", nodes.escalation_node)
    graph.add_node("finalize", nodes.finalize_node)

    graph.add_edge(START, "triage")

    # Dynamic router (spec section 20): fans out into 1-4 specialist nodes running in
    # parallel in the same superstep, or routes straight to escalation on an explicit
    # human request / unrecognized intent. Whichever specialists actually run all converge
    # on "resolution" once LangGraph has finished that superstep (automatic fan-in).
    triage_path_map = {name: name for name in (*SPECIALIST_NODES, "escalation")}
    graph.add_conditional_edges("triage", route_after_triage, triage_path_map)

    for specialist in SPECIALIST_NODES:
        graph.add_edge(specialist, "resolution")

    graph.add_edge("resolution", "qa")

    # Reflection loop (spec section 21): QA can send the workflow back to "resolution" up to
    # MAX_ITERATIONS times before it is forced to "escalation" instead of looping forever.
    graph.add_conditional_edges(
        "qa", route_after_qa, {"resolution": "resolution", "escalation": "escalation", "finalize": "finalize"}
    )

    graph.add_edge("escalation", END)
    graph.add_edge("finalize", END)

    return graph.compile()


_compiled_graph: CompiledStateGraph | None = None


def get_support_graph() -> CompiledStateGraph:
    """Return the compiled support graph, building it once and reusing it thereafter."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_support_graph()
    return _compiled_graph


async def run_support_workflow(
    customer_id: str,
    customer_message: str,
    conversation_history: list[str] | None = None,
) -> SupportState:
    """Build the initial state and run the full support workflow, returning the final state."""
    logger.info("support_workflow_start customer_id=%s", customer_id)
    initial_state = build_initial_state(customer_id, customer_message, conversation_history)
    graph = get_support_graph()
    final_state: SupportState = await graph.ainvoke(initial_state)
    logger.info(
        "support_workflow_end customer_id=%s escalation_required=%s human_approval_required=%s",
        customer_id,
        final_state.get("escalation_required"),
        final_state.get("human_approval_required"),
    )
    return final_state
