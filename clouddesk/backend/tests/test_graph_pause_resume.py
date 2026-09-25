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
    monkeypatch.setattr("app.graph.resolution_nodes.run_resolution_agent", AsyncMock(return_value=_resolution()))
    monkeypatch.setattr("app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=_qa_approved()))


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
    # Regression test for the Phase 5-era status-lag bug (spec section 33 Definition of Done):
    # `human_approval_required` must be reset to False once a paused run actually resumes and
    # concludes — app.graph.resolution_nodes.await_human_decision_node used to leave it True
    # forever (no reducer merges it; only overwrite-on-update), so a resumed run's final state
    # looked identical to a still-paused one to any caller reading this flag, including
    # app.services.conversation_service._derive_status (see test below for that caller's view).
    assert final_state["human_approval_required"] is False


async def test_resume_with_approval_updates_conversation_status_to_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end regression test for the conversation-status-lag bug at the API-facing layer:
    a resumed, concluded run must be reported as "completed" (not stuck on "awaiting_approval")
    by app.services.conversation_service, exactly what GET /api/v1/conversations/{thread_id}
    returns to a polling customer.
    """
    from app.database.session import get_session
    from app.models.conversation import ConversationRecord
    from app.services import conversation_service

    _patch_agents(monkeypatch)
    paused_state = await run_support_workflow(_CUSTOMER_ID, "Why was I charged twice?")
    thread_id = paused_state["thread_id"]

    # Persist a conversation record the same way app.services.conversation_service.
    # start_conversation would have, so record_resumed_workflow (called by app.api.v1.approvals
    # after a decision) has a row to update. Written directly to the `conversation_records` table
    # (not the dict this module used before the 2026-09-25 persistence fix) so this test also
    # doubles as proof that a resume updates the durable record, not just an in-memory one.
    async with get_session() as session:
        session.add(ConversationRecord(thread_id=thread_id, customer_id=_CUSTOMER_ID, status="awaiting_approval"))
        await session.commit()

    decision = {"actions": [{"action_id": "n/a", "status": "approved"}]}
    final_state = await resume_support_workflow(thread_id, decision)
    await conversation_service.record_resumed_workflow(thread_id, final_state)

    record = await conversation_service.get_conversation(thread_id)
    assert record.status == "completed"


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


async def test_resume_survives_a_simulated_backend_restart(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression test for the production-hardening fix this module exists to prove (README's
    former "Production Deployment" gap, flagged in the Phase 5 and Phase 9 reports): a paused
    thread must be resumable even after the backend process that paused it is gone.

    A real OS-level process restart is exercised manually (see the task's verification step); this
    test simulates the in-process consequence of one as closely as pytest allows — it discards
    BOTH the cached compiled graph AND the checkpointer's connection pool
    (app.graph.graph.close_checkpointer), exactly what happens to `app.graph.graph`'s module
    globals when a fresh Python process starts. `resume_support_workflow` is then called against a
    rebuilt-from-scratch checkpointer, so this can only pass if the paused run's state was truly
    persisted to Postgres — nothing from the original run is left in memory.
    """
    from app.graph import graph as graph_module

    _patch_agents(monkeypatch)
    paused_state = await run_support_workflow(_CUSTOMER_ID, "Why was I charged twice?")
    thread_id = paused_state["thread_id"]

    await graph_module.close_checkpointer()
    assert graph_module._checkpointer is None
    assert graph_module._compiled_graph is None

    decision = {"actions": [{"action_id": "n/a", "status": "approved"}]}
    final_state = await resume_support_workflow(thread_id, decision)

    assert final_state["approved_actions"]
    assert final_state["executed_actions"]
    assert "approved and completed" in final_state["final_response"]
    assert final_state["human_approval_required"] is False
