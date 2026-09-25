# tests/test_graph_routing.py
# Purpose: Unit tests for the pure routing functions (app.graph.routing) that implement the
#          spec section 20 dynamic fan-out and the section 21 reflection loop. No LLM, no graph
#          execution — these are plain function calls against hand-built SupportState dicts.
# Author: CloudDesk Team
# Date: 2026-09-24

from app.graph.routing import MAX_ITERATIONS, route_after_qa, route_after_triage
from app.graph.state import build_initial_state


def _state_with(**overrides: object) -> dict[str, object]:
    state = build_initial_state("cust-1", "test message")
    state.update(overrides)
    return state


def test_route_after_triage_single_specialist() -> None:
    state = _state_with(required_agents=["billing"])
    assert route_after_triage(state) == ["billing"]


def test_route_after_triage_multiple_specialists_fan_out() -> None:
    state = _state_with(required_agents=["billing", "account", "technical"])
    assert route_after_triage(state) == ["billing", "account", "technical"]


def test_route_after_triage_explicit_escalation_flag() -> None:
    state = _state_with(required_agents=["escalation"])
    assert route_after_triage(state) == ["escalation"]


def test_route_after_triage_escalation_alongside_specialist_still_investigates() -> None:
    """If triage lists escalation alongside a real specialist (e.g. a severe-but-investigable
    billing issue), the specialist still runs first rather than skipping investigation entirely —
    only an explicit human request in the customer's own words should do that (spec Scenario G)."""
    state = _state_with(required_agents=["escalation", "billing"])
    assert route_after_triage(state) == ["billing"]


def test_route_after_triage_keyword_fallback_for_explicit_human_request() -> None:
    state = _state_with(
        customer_message="I want to speak to a human please.", required_agents=["billing"]
    )
    assert route_after_triage(state) == ["escalation"]


def test_route_after_triage_no_recognized_specialist_falls_back_to_escalation() -> None:
    state = _state_with(required_agents=[])
    assert route_after_triage(state) == ["escalation"]


def test_route_after_qa_approved_goes_to_finalize() -> None:
    state = _state_with(qa_result={"approved": True}, iteration=1)
    assert route_after_qa(state) == "finalize"


def test_route_after_qa_not_approved_below_max_goes_to_resolution() -> None:
    state = _state_with(qa_result={"approved": False}, iteration=1)
    assert route_after_qa(state) == "resolution"


def test_route_after_qa_not_approved_at_max_iterations_goes_to_escalation() -> None:
    state = _state_with(qa_result={"approved": False}, iteration=MAX_ITERATIONS)
    assert route_after_qa(state) == "escalation"


def test_max_iterations_constant_is_three() -> None:
    assert MAX_ITERATIONS == 3
