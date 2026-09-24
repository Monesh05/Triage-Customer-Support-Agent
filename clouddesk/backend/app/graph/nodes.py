# app/graph/nodes.py
# Purpose: LangGraph node functions for the "front half" of the support StateGraph — triage and
#          the four specialist nodes (spec sections 9-13). Each node wraps exactly one Phase 3
#          agent call, translating its `SchemaT | AgentError` result into a partial SupportState
#          update. No node ever lets an exception or AgentError propagate/crash the graph —
#          failures degrade to an `errors` entry and a safe fallback instead. See
#          app.graph.resolution_nodes for resolution/qa/escalation/finalize/await_human_decision
#          (split into its own module purely to keep both files under this codebase's
#          300-line-per-file guideline).
#
#          Phase 7 (spec section 24) wraps every node here in
#          `app.observability.tracer.trace_agent_run`, which times the call and persists a
#          redacted `AgentRun` row for it. Tracing failures are swallowed inside
#          `trace_agent_run` itself and never affect the return values below.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging
import uuid
from typing import Any

from app.agents.account import run_account_agent
from app.agents.base import AgentError
from app.agents.billing import run_billing_agent
from app.agents.product import run_product_agent
from app.agents.technical import run_technical_agent
from app.agents.triage import run_triage_agent
from app.graph.state import SupportState, parse_ticket_uuid
from app.observability.tracer import trace_agent_run

logger = logging.getLogger("clouddesk.graph.nodes")


async def triage_node(state: SupportState) -> dict[str, Any]:
    """Classify the customer message (spec section 9). No tools; pure classification."""
    logger.info("node_enter node=triage")
    async with trace_agent_run(
        thread_id=state["thread_id"], ticket_id=parse_ticket_uuid(state), agent_name="triage"
    ) as recorder:
        recorder.set_input(state["customer_message"])
        try:
            result = await run_triage_agent(state["customer_message"], state["conversation_history"])
        except Exception as exc:  # noqa: BLE001
            result = AgentError(agent="triage", message=str(exc))
        if isinstance(result, AgentError):
            recorder.mark_failure(result.message)
            logger.info("node_exit node=triage status=error")
            return {
                "errors": [f"triage: {result.message}"],
                "intents": ["other"],
                "priority": "high",
                "sentiment": "neutral",
                "required_agents": ["escalation"],
            }
        recorder.set_output(result)
        logger.info("node_exit node=triage status=ok required_agents=%s", result.required_agents)
        return {
            "intents": list(result.intents),
            "priority": result.priority,
            "sentiment": result.sentiment,
            "required_agents": list(result.required_agents),
        }


async def _run_specialist(
    node_name: str, coroutine: Any, *, thread_id: str, ticket_id: uuid.UUID | None, input_text: str
) -> dict[str, Any]:
    """Shared wrapper: run one specialist agent call, store its result/error under its own key."""
    logger.info("node_enter node=%s", node_name)
    async with trace_agent_run(thread_id=thread_id, ticket_id=ticket_id, agent_name=node_name) as recorder:
        recorder.set_input(input_text)
        try:
            result = await coroutine
        except Exception as exc:  # noqa: BLE001
            result = AgentError(agent=node_name, message=str(exc))
        if isinstance(result, AgentError):
            recorder.mark_failure(result.message)
            logger.info("node_exit node=%s status=error", node_name)
            return {
                "errors": [f"{node_name}: {result.message}"],
                "specialist_results": {node_name: {"error": result.message}},
            }
        recorder.set_output(result)
        logger.info("node_exit node=%s status=ok", node_name)
        return {"specialist_results": {node_name: result.model_dump()}}


async def billing_node(state: SupportState) -> dict[str, Any]:
    """Investigate billing (spec section 10). Runs only when routed by route_after_triage."""
    return await _run_specialist(
        "billing",
        run_billing_agent(state["customer_id"], state["customer_message"]),
        thread_id=state["thread_id"],
        ticket_id=parse_ticket_uuid(state),
        input_text=state["customer_message"],
    )


async def account_node(state: SupportState) -> dict[str, Any]:
    """Investigate account/access/entitlements (spec section 11)."""
    return await _run_specialist(
        "account",
        run_account_agent(state["customer_id"], state["customer_message"]),
        thread_id=state["thread_id"],
        ticket_id=parse_ticket_uuid(state),
        input_text=state["customer_message"],
    )


async def technical_node(state: SupportState) -> dict[str, Any]:
    """Investigate API/technical issues (spec section 12)."""
    return await _run_specialist(
        "technical",
        run_technical_agent(state["customer_id"], state["customer_message"]),
        thread_id=state["thread_id"],
        ticket_id=parse_ticket_uuid(state),
        input_text=state["customer_message"],
    )


async def product_node(state: SupportState) -> dict[str, Any]:
    """Answer product/documentation questions (spec section 13)."""
    return await _run_specialist(
        "product",
        run_product_agent(state["customer_message"]),
        thread_id=state["thread_id"],
        ticket_id=parse_ticket_uuid(state),
        input_text=state["customer_message"],
    )
