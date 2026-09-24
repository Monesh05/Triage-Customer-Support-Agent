# evaluation/tests/test_metrics.py
# Purpose: Unit tests for every evaluation/metrics/*.py scoring function, feeding hand-crafted
#          `TicketOutcome`s (no real graph/DB/LLM call) and asserting the computed numbers are
#          exactly what the documented methodology should produce.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid

from evaluation.datasets.schema import DatasetRecord
from evaluation.metrics.escalation import escalation_accuracy, false_positive_escalation_rate
from evaluation.metrics.latency import average_iterations, average_latency_ms
from evaluation.metrics.models import AgentRunView, TicketOutcome
from evaluation.metrics.qa import hallucination_rate, qa_accuracy
from evaluation.metrics.resolution import resolution_accuracy
from evaluation.metrics.routing import intent_classification_accuracy, jaccard_similarity, routing_accuracy
from evaluation.metrics.tool_calls import tool_call_accuracy


def _record(**overrides) -> DatasetRecord:
    defaults = dict(
        ticket_id="t-1",
        category="billing",
        customer_id=str(uuid.uuid4()),
        customer_message="I was charged twice.",
        expected_intents=["billing"],
        expected_required_agents=["billing"],
        expected_priority="high",
        expected_escalation=False,
    )
    defaults.update(overrides)
    return DatasetRecord(**defaults)


def _outcome(record: DatasetRecord, final_state: dict | None, trace: list[AgentRunView] | None = None,
             latency_ms: float | None = None, run_error: str | None = None) -> TicketOutcome:
    return TicketOutcome(
        record=record, final_state=final_state, trace=trace or [], total_latency_ms=latency_ms, run_error=run_error
    )


def test_jaccard_similarity_exact_match_is_one() -> None:
    assert jaccard_similarity(["billing"], ["billing"]) == 1.0


def test_jaccard_similarity_disjoint_is_zero() -> None:
    assert jaccard_similarity(["billing"], ["technical"]) == 0.0


def test_jaccard_similarity_partial_overlap() -> None:
    assert jaccard_similarity(["billing", "technical"], ["billing"]) == 0.5


def test_intent_classification_accuracy_averages_over_tickets() -> None:
    perfect = _outcome(_record(expected_intents=["billing"]), {"intents": ["billing"]})
    wrong = _outcome(_record(expected_intents=["billing"]), {"intents": ["technical"]})
    assert intent_classification_accuracy([perfect, wrong]) == 0.5


def test_intent_classification_accuracy_ignores_failed_tickets() -> None:
    perfect = _outcome(_record(expected_intents=["billing"]), {"intents": ["billing"]})
    failed = _outcome(_record(), None, run_error="boom")
    assert intent_classification_accuracy([perfect, failed]) == 1.0


def test_routing_accuracy_exact_match() -> None:
    outcome = _outcome(_record(expected_required_agents=["billing", "account"]),
                        {"required_agents": ["billing", "account"]})
    assert routing_accuracy([outcome]) == 1.0


def test_tool_call_accuracy_full_overlap() -> None:
    trace = [AgentRunView(agent_name="billing", status="success", duration_ms=100,
                           tool_calls=[{"tool": "get_payment_history"}, {"tool": "calculate_refund"}])]
    record = _record(category="product")
    outcome = _outcome(record, {"intents": ["product"]}, trace=trace)
    # "product" category expects only search_product_docs; no overlap -> 0.0
    assert tool_call_accuracy([outcome]) == 0.0


def test_tool_call_accuracy_uncategorized_ticket_is_excluded() -> None:
    outcome = _outcome(_record(category="ambiguous"), {"intents": []}, trace=[])
    assert tool_call_accuracy([outcome]) == 0.0


def test_resolution_accuracy_matches_expected_keyword() -> None:
    record = _record(expected_resolution_keywords=["refund"])
    state = {"resolution": {"proposed_resolution": "A refund request should be created.",
                             "customer_facing_draft": "We will refund you."}}
    assert resolution_accuracy([_outcome(record, state)]) == 1.0


def test_resolution_accuracy_flags_forbidden_keyword() -> None:
    record = _record(forbidden_resolution_keywords=["5000"])
    state = {"resolution": {"proposed_resolution": "A $5000 refund was processed.",
                             "customer_facing_draft": "Done."}}
    assert resolution_accuracy([_outcome(record, state)]) == 0.0


def test_resolution_accuracy_excludes_tickets_without_a_resolution() -> None:
    outcome = _outcome(_record(), {"resolution": None})
    assert resolution_accuracy([outcome]) == 0.0


def test_qa_accuracy_matches_expectation() -> None:
    record = _record(expect_qa_approval=False)
    state = {"qa_result": {"approved": False}}
    assert qa_accuracy([_outcome(record, state)]) == 1.0


def test_qa_accuracy_ignores_unlabeled_tickets() -> None:
    outcome = _outcome(_record(expect_qa_approval=None), {"qa_result": {"approved": True}})
    assert qa_accuracy([outcome]) == 0.0


def test_hallucination_rate_counts_flagged_tickets() -> None:
    flagged = _outcome(_record(), {"qa_result": {"hallucination_detected": True}})
    clean = _outcome(_record(), {"qa_result": {"hallucination_detected": False}})
    assert hallucination_rate([flagged, clean]) == 0.5


def test_escalation_accuracy_exact_match() -> None:
    correct = _outcome(_record(expected_escalation=True), {"escalation_required": True})
    wrong = _outcome(_record(expected_escalation=False), {"escalation_required": True})
    assert escalation_accuracy([correct, wrong]) == 0.5


def test_false_positive_escalation_rate() -> None:
    wrongly_escalated = _outcome(_record(is_false_positive=True, expected_escalation=False),
                                  {"escalation_required": True})
    correctly_not_escalated = _outcome(_record(is_false_positive=True, expected_escalation=False),
                                        {"escalation_required": False})
    assert false_positive_escalation_rate([wrongly_escalated, correctly_not_escalated]) == 0.5


def test_false_positive_escalation_rate_ignores_non_false_positive_tickets() -> None:
    outcome = _outcome(_record(is_false_positive=False), {"escalation_required": True})
    assert false_positive_escalation_rate([outcome]) == 0.0


def test_average_latency_ms() -> None:
    a = _outcome(_record(), {"iteration": 1}, latency_ms=1000.0)
    b = _outcome(_record(), {"iteration": 1}, latency_ms=3000.0)
    assert average_latency_ms([a, b]) == 2000.0


def test_average_iterations() -> None:
    a = _outcome(_record(), {"iteration": 1})
    b = _outcome(_record(), {"iteration": 3})
    assert average_iterations([a, b]) == 2.0
