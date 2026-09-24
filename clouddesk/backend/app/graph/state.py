# app/graph/state.py
# Purpose: The shared LangGraph state (spec section 18) threaded through every node of the
#          support workflow. Extends the spec's example TypedDict with three small,
#          justified additions: `escalation_result` (the Escalation Agent's structured
#          handoff, spec section 17), `final_response` (the customer-facing text produced
#          once the workflow reaches finalize/escalation), and `thread_id` (Phase 5, spec
#          section 22: the LangGraph checkpoint thread id for this run, so a caller/API can
#          correlate a paused run with the persisted approval record and resume it later) —
#          all read by API/UI callers that only see the final state, not individual node outputs.
# Author: CloudDesk Team
# Date: 2026-09-24

import operator
import uuid
from typing import Annotated, TypedDict


def merge_dicts(
    existing: dict[str, dict[str, object]], update: dict[str, dict[str, object]]
) -> dict[str, dict[str, object]]:
    """Reducer for `specialist_results`: parallel specialist nodes (billing/account/technical/
    product) run in the same LangGraph superstep and each return one key of this dict. Without
    a custom reducer, LangGraph's default overwrite-on-conflict behavior would raise an
    InvalidUpdateError when two branches update the same field concurrently — this merges their
    updates into one dict instead.
    """
    merged = dict(existing)
    merged.update(update)
    return merged


class SupportState(TypedDict):
    """Shared state passed between every node in the support StateGraph (spec section 18)."""

    customer_id: str
    customer_message: str
    conversation_history: list[str]

    intents: list[str]
    priority: str
    sentiment: str
    required_agents: list[str]

    specialist_results: Annotated[dict[str, dict[str, object]], merge_dicts]

    resolution: dict[str, object] | None
    qa_result: dict[str, object] | None

    escalation_required: bool
    human_approval_required: bool

    pending_actions: list[dict[str, object]]
    approved_actions: list[dict[str, object]]
    executed_actions: list[dict[str, object]]

    # Parallel specialist branches may each append an error in the same superstep; `operator.add`
    # concatenates their lists instead of one overwriting the other (same conflict as above).
    errors: Annotated[list[str], operator.add]

    iteration: int

    # Small, justified additions beyond the spec §18 example:
    escalation_result: dict[str, object] | None
    final_response: str | None
    thread_id: str


def build_initial_state(
    customer_id: str,
    customer_message: str,
    conversation_history: list[str] | None = None,
    thread_id: str | None = None,
) -> SupportState:
    """Construct a fresh SupportState for a new support-workflow invocation.

    `thread_id` identifies the LangGraph checkpoint thread (Phase 5); a fresh one is generated
    when not supplied, so every top-level call to `run_support_workflow` gets its own thread.
    """
    return SupportState(
        customer_id=customer_id,
        customer_message=customer_message,
        conversation_history=list(conversation_history or []),
        intents=[],
        priority="medium",
        sentiment="neutral",
        required_agents=[],
        specialist_results={},
        resolution=None,
        qa_result=None,
        escalation_required=False,
        human_approval_required=False,
        pending_actions=[],
        approved_actions=[],
        executed_actions=[],
        errors=[],
        iteration=0,
        escalation_result=None,
        final_response=None,
        thread_id=thread_id or str(uuid.uuid4()),
    )
