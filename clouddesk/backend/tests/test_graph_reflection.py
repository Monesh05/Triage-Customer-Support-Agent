# tests/test_graph_reflection.py
# Purpose: Tests for the QA reflection loop (spec section 21): QA rejecting a resolution sends
#          the graph back to "resolution" (bounded by MAX_ITERATIONS), and repeated rejection
#          forces escalation instead of looping forever. All agents mocked — no real LLM calls.
# Author: CloudDesk Team
# Date: 2026-09-24

from unittest.mock import AsyncMock

import pytest

from app.agents.schemas import (
    EscalationAgentResult,
    ProductAgentResult,
    QAAgentResult,
    ResolutionAgentResult,
    TriageResult,
)
from app.graph.graph import run_support_workflow
from app.graph.routing import MAX_ITERATIONS

RESOLUTION_PAYLOAD: dict[str, object] = {
    "summary": "Synthesis.",
    "issues_identified": [],
    "proposed_resolution": "Do the thing.",
    "customer_facing_draft": "Here is your answer.",
    "unresolved_questions": [],
    "requires_approval": False,
}


def _qa_payload(approved: bool) -> dict[str, object]:
    return {
        "approved": approved,
        "issues": [] if approved else ["draft is incomplete"],
        "required_changes": [] if approved else ["add more detail"],
        "evidence_supported": True,
        "hallucination_detected": False,
        "policy_compliant": True,
        "actions_confirmed": True,
        "escalation_needed": False,
    }


def _patch_triage_and_product(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(
            return_value=TriageResult(
                intents=["product"], priority="low", sentiment="neutral", required_agents=["product"], reason="faq"
            )
        ),
    )
    monkeypatch.setattr(
        "app.graph.nodes.run_product_agent",
        AsyncMock(return_value=ProductAgentResult(answer="Yes.", sources=[], grounded=False)),
    )


async def test_qa_rejects_then_approves_retries_resolution_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """QA fails on the first pass, approves on the second: resolution runs twice, ends finalized."""
    _patch_triage_and_product(monkeypatch)
    resolution_mock = AsyncMock(return_value=ResolutionAgentResult.model_validate(RESOLUTION_PAYLOAD))
    monkeypatch.setattr("app.graph.nodes.run_resolution_agent", resolution_mock)

    qa_mock = AsyncMock(
        side_effect=[
            QAAgentResult.model_validate(_qa_payload(False)),
            QAAgentResult.model_validate(_qa_payload(True)),
        ]
    )
    monkeypatch.setattr("app.graph.nodes.run_qa_agent", qa_mock)

    final_state = await run_support_workflow("cust-1", "Does Pro include API access?")

    assert resolution_mock.await_count == 2
    assert qa_mock.await_count == 2
    assert final_state["iteration"] == 2
    assert final_state["escalation_required"] is False
    assert final_state["final_response"] == RESOLUTION_PAYLOAD["customer_facing_draft"]


async def test_qa_repeatedly_failing_stops_at_max_iterations_and_escalates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """QA never approves: the graph must stop after MAX_ITERATIONS resolution attempts, not hang."""
    _patch_triage_and_product(monkeypatch)
    resolution_mock = AsyncMock(return_value=ResolutionAgentResult.model_validate(RESOLUTION_PAYLOAD))
    monkeypatch.setattr("app.graph.nodes.run_resolution_agent", resolution_mock)
    qa_mock = AsyncMock(return_value=QAAgentResult.model_validate(_qa_payload(False)))
    monkeypatch.setattr("app.graph.nodes.run_qa_agent", qa_mock)

    escalation_mock = AsyncMock(
        return_value=EscalationAgentResult(
            customer="cust-1",
            issue="QA never approved the resolution.",
            intent=["product"],
            priority="low",
            investigation_performed=[],
            evidence=[],
            actions_attempted=[],
            unresolved_questions=[],
            recommended_human_action="A human should review this FAQ answer manually.",
            conversation_history=[],
        )
    )
    monkeypatch.setattr("app.graph.nodes.run_escalation_agent", escalation_mock)

    final_state = await run_support_workflow("cust-1", "Does Pro include API access?")

    assert resolution_mock.await_count == MAX_ITERATIONS
    assert qa_mock.await_count == MAX_ITERATIONS
    escalation_mock.assert_awaited_once()
    assert final_state["escalation_required"] is True
    assert final_state["escalation_result"] is not None
