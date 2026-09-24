# tests/test_graph_pause_resume.py
# Purpose: Tests for the Phase 5 human-in-the-loop pause/resume mechanism (spec section 22).
#          Every `app.agents.*` entrypoint is mocked (same policy as
#          tests/test_graph_scenarios.py) to produce a billing result with a
#          `requires_approval=True` refund recommendation, so these tests exercise ONLY the
#          graph's interrupt/resume mechanics: a paused run must actually stop (not silently run
#          to a "resolved" completion) and expose a resumable thread id, and
#          `resume_support_workflow` must be able to complete it afterwards on both the
#          approve and reject paths.
# Author: CloudDesk Team
# Date: 2026-09-24

from unittest.mock import AsyncMock

import pytest

from app.agents.schemas import (
    BillingAgentResult,
    QAAgentResult,
    RecommendedAction,
    ResolutionAgentResult,
    TriageResult,
)
from app.graph.graph import resume_support_workflow, run_support_workflow
from app.services.exceptions import InvalidStateError

_CUSTOMER_ID = "cust-pause-resume-1"


def _triage() -> TriageResult:
    return TriageResult(
        intents=["billing"], priority="medium", sentiment="neutral",
        required_agents=["billing"], reason="Billing dispute.",
    )


def _billing_requires_approval() -> BillingAgentResult:
    return BillingAgentResult(
        status="resolved",
        findings=[{"fact": "Two identical payments found for the same billing period."}],
        recommended_actions=[RecommendedAction(action="Refund duplicate payment", amount=49.0, requires_approval=True)],
        evidence=["PAY_1", "PAY_2"],
    )


def _resolution() -> ResolutionAgentResult:
    return ResolutionAgentResult.model_validate(
        {
            "summary": "Duplicate charge confirmed.",
            "issues_identified": ["duplicate charge"],
            "proposed_resolution": "Refund the duplicate payment.",
            "customer_facing_draft": "We found a duplicate charge and will refund it.",
            "unresolved_questions": [],
            "requires_approval": True,
        }
    )


def _qa_approved() -> QAAgentResult:
    return QAAgentResult.model_validate(
        {
            "approved": True, "issues": [], "required_changes": [],
            "evidence_supported": True, "hallucination_detected": False,
            "policy_compliant": True, "actions_confirmed": True, "escalation_needed": False,
        }
    )


def _patch_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.graph.nodes.run_triage_agent", AsyncMock(return_value=_triage()))
    monkeypatch.setattr("app.graph.nodes.run_billing_agent", AsyncMock(return_value=_billing_requires_approval()))
    monkeypatch.setattr("app.graph.nodes.run_resolution_agent", AsyncMock(return_value=_resolution()))
    monkeypatch.setattr("app.graph.nodes.run_qa_agent", AsyncMock(return_value=_qa_approved()))


async def test_workflow_pauses_and_does_not_produce_a_resolved_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_agents(monkeypatch)

    paused_state = await run_support_workflow(_CUSTOMER_ID, "Why was I charged twice?")

    assert paused_state["human_approval_required"] is True
    assert paused_state["thread_id"]
    assert paused_state["pending_actions"]
    assert paused_state["pending_actions"][0]["agent"] == "billing"
    # Not yet resolved: the customer message is the "pending approval" draft, and no action has
    # been recorded as approved/executed yet.
    assert "approval" in paused_state["final_response"].lower()
    assert paused_state["approved_actions"] == []
    assert paused_state["executed_actions"] == []


async def test_resume_with_approval_completes_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_agents(monkeypatch)
    paused_state = await run_support_workflow(_CUSTOMER_ID, "Why was I charged twice?")
    thread_id = paused_state["thread_id"]

    decision = {"actions": [{"action_id": "n/a", "status": "approved"}]}
    final_state = await resume_support_workflow(thread_id, decision)

    assert final_state["approved_actions"]
    assert final_state["executed_actions"]
    assert "approved and completed" in final_state["final_response"]


async def test_resume_with_rejection_produces_explanatory_response(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_agents(monkeypatch)
    paused_state = await run_support_workflow(_CUSTOMER_ID, "Why was I charged twice?")
    thread_id = paused_state["thread_id"]

    decision = {"actions": [{"action_id": "n/a", "status": "rejected"}]}
    final_state = await resume_support_workflow(thread_id, decision)

    assert final_state["approved_actions"] == []
    assert final_state["executed_actions"] == []
    assert "not approved" in final_state["final_response"].lower()


async def test_resume_unknown_thread_raises_invalid_state(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_agents(monkeypatch)

    with pytest.raises(InvalidStateError):
        await resume_support_workflow("thread-that-was-never-paused", {"actions": []})
