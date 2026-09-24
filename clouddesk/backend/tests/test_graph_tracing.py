# tests/test_graph_tracing.py
# Purpose: End-to-end (mocked-agent) tests of Phase 7's Agent Observability instrumentation
#          (spec section 24). Uses `committed_session` (not the rolled-back `db_session`)
#          because ticket auto-creation and AgentRun persistence both go through
#          app.database.session.get_session() on their own DB connection, same as every Phase 2
#          tool test. Agents are mocked at the `app.graph.nodes.run_X_agent` level (same policy
#          as tests/test_graph_scenarios.py) EXCEPT in the tool-call-capture test, where the real
#          Billing Agent runs against a fake LLM client so its real tool loop (app.agents.base)
#          actually executes and reports a tool call to the tracer.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import (
    AccountAgentResult,
    BillingAgentResult,
    ProductAgentResult,
    QAAgentResult,
    RecommendedAction,
    ResolutionAgentResult,
    TechnicalAgentResult,
    TriageResult,
)
from app.graph.graph import run_support_workflow
from app.llm.structured import AgentError
from app.models.enums import AgentRunStatus
from app.services import observability_service
from app.tools.base import ToolResult
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage, FakeToolCall
from tests.factories import create_customer_with_account, create_org_and_plan


async def _register_customer(committed_session: AsyncSession) -> str:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    await committed_session.commit()
    committed_session.info["created_org_ids"].append(org.id)
    return str(customer.id)


def _resolution(requires_approval: bool = False) -> ResolutionAgentResult:
    return ResolutionAgentResult.model_validate(
        {
            "summary": "Synthesis.",
            "issues_identified": [],
            "proposed_resolution": "Do the thing.",
            "customer_facing_draft": "Here is your answer.",
            "unresolved_questions": [],
            "requires_approval": requires_approval,
        }
    )


def _qa(approved: bool) -> QAAgentResult:
    return QAAgentResult.model_validate(
        {
            "approved": approved,
            "issues": [] if approved else ["needs work"],
            "required_changes": [] if approved else ["fix it"],
            "evidence_supported": True,
            "hallucination_detected": False,
            "policy_compliant": True,
            "actions_confirmed": True,
            "escalation_needed": False,
        }
    )


async def test_multi_intent_workflow_records_one_run_per_specialist(
    committed_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Billing+account+technical run in parallel: expect a trace row for triage, each of the
    three specialists, resolution (iteration 1) and qa (iteration 1) — six rows, all success."""
    customer_id = await _register_customer(committed_session)

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(
            return_value=TriageResult(
                intents=["billing", "account", "technical"], priority="medium", sentiment="neutral",
                required_agents=["billing", "account", "technical"], reason="multi",
            )
        ),
    )
    monkeypatch.setattr(
        "app.graph.nodes.run_billing_agent",
        AsyncMock(
            return_value=BillingAgentResult(
                status="resolved", findings=[], recommended_actions=[], evidence=["PAY_1"]
            )
        ),
    )
    monkeypatch.setattr(
        "app.graph.nodes.run_account_agent",
        AsyncMock(return_value=AccountAgentResult(status="resolved", findings=[], recommended_actions=[], evidence=[])),
    )
    monkeypatch.setattr(
        "app.graph.nodes.run_technical_agent",
        AsyncMock(return_value=TechnicalAgentResult(hypothesis="n/a", status="resolved", evidence=[], recommended_actions=[])),
    )
    monkeypatch.setattr("app.graph.resolution_nodes.run_resolution_agent", AsyncMock(return_value=_resolution()))
    monkeypatch.setattr("app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=_qa(True)))

    final_state = await run_support_workflow(customer_id, "Upgraded, charged twice, API broken.")

    assert final_state["ticket_id"] is not None
    ticket_uuid = uuid.UUID(final_state["ticket_id"])
    trace = await observability_service.get_trace_for_ticket(committed_session, ticket_uuid)

    agent_names = [run.agent_name for run in trace]
    assert len(agent_names) == 6
    assert agent_names[0] == "triage"
    assert set(agent_names[1:4]) == {"billing", "account", "technical"}
    assert agent_names[4:] == ["resolution", "qa"]
    assert all(run.status == AgentRunStatus.SUCCESS for run in trace)
    resolution_run = next(run for run in trace if run.agent_name == "resolution")
    qa_run = next(run for run in trace if run.agent_name == "qa")
    assert resolution_run.iteration == 1
    assert qa_run.iteration == 1


async def test_qa_reflection_loop_records_iteration_numbers(
    committed_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QA rejects once then approves: resolution/qa each run twice, with iteration 1 then 2."""
    customer_id = await _register_customer(committed_session)

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
    monkeypatch.setattr("app.graph.resolution_nodes.run_resolution_agent", AsyncMock(return_value=_resolution()))
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_qa_agent", AsyncMock(side_effect=[_qa(False), _qa(True)])
    )

    final_state = await run_support_workflow(customer_id, "Does Pro include API access?")

    ticket_uuid = uuid.UUID(final_state["ticket_id"])
    trace = await observability_service.get_trace_for_ticket(committed_session, ticket_uuid)

    resolution_iterations = [run.iteration for run in trace if run.agent_name == "resolution"]
    qa_iterations = [run.iteration for run in trace if run.agent_name == "qa"]
    assert resolution_iterations == [1, 2]
    assert qa_iterations == [1, 2]
    assert all(run.status == AgentRunStatus.SUCCESS for run in trace)


async def test_specialist_failure_is_recorded_with_failure_status_and_error(
    committed_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    customer_id = await _register_customer(committed_session)

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(
            return_value=TriageResult(
                intents=["billing"], priority="medium", sentiment="neutral", required_agents=["billing"], reason="x"
            )
        ),
    )
    monkeypatch.setattr(
        "app.graph.nodes.run_billing_agent",
        AsyncMock(return_value=AgentError(agent="billing", message="LLM timed out")),
    )
    monkeypatch.setattr("app.graph.resolution_nodes.run_resolution_agent", AsyncMock(return_value=_resolution()))
    monkeypatch.setattr("app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=_qa(True)))

    final_state = await run_support_workflow(customer_id, "I was charged twice.")

    ticket_uuid = uuid.UUID(final_state["ticket_id"])
    trace = await observability_service.get_trace_for_ticket(committed_session, ticket_uuid)

    billing_run = next(run for run in trace if run.agent_name == "billing")
    assert billing_run.status == AgentRunStatus.FAILURE
    assert billing_run.error is not None
    assert "LLM timed out" in billing_run.error


async def test_billing_tool_calls_are_captured_on_the_agent_run(
    committed_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real Billing Agent (not mocked) runs its bounded tool loop against a fake LLM; the
    resulting `AgentRun` row for "billing" must record the tool it called."""
    customer_id = await _register_customer(committed_session)

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(
            return_value=TriageResult(
                intents=["billing"], priority="medium", sentiment="neutral", required_agents=["billing"], reason="x"
            )
        ),
    )
    monkeypatch.setattr("app.graph.resolution_nodes.run_resolution_agent", AsyncMock(return_value=_resolution()))
    monkeypatch.setattr("app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=_qa(True)))

    fake_llm = FakeLLM()
    tool_call = FakeToolCall("call_1", "get_payment_history", json.dumps({"customer_id": customer_id}))
    fake_llm.client.chat.completions.create.side_effect = [
        FakeCompletion(FakeMessage(tool_calls=[tool_call])),
        FakeCompletion(FakeMessage(content=None, tool_calls=None)),
    ]
    expected = BillingAgentResult(
        status="resolved", findings=[], recommended_actions=[], evidence=["PAY_123"]
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(FakeMessage(parsed=expected))
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr(
        "app.agents.billing.billing_tools.get_payment_history",
        AsyncMock(return_value=ToolResult(success=True, data=[])),
    )

    final_state = await run_support_workflow(customer_id, "I was charged twice.")

    ticket_uuid = uuid.UUID(final_state["ticket_id"])
    trace = await observability_service.get_trace_for_ticket(committed_session, ticket_uuid)

    billing_run = next(run for run in trace if run.agent_name == "billing")
    assert len(billing_run.tool_calls) == 1
    assert billing_run.tool_calls[0]["tool"] == "get_payment_history"
    assert len(billing_run.tool_results) == 1


async def test_tracing_persist_failure_does_not_break_the_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the observability layer's DB write blows up, `run_support_workflow` must still return a
    normal, complete final state — a tracing failure is logged and swallowed, never raised."""
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
    monkeypatch.setattr("app.graph.resolution_nodes.run_resolution_agent", AsyncMock(return_value=_resolution()))
    monkeypatch.setattr("app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=_qa(True)))
    monkeypatch.setattr(
        "app.observability.tracer.observability_service.create_agent_run",
        AsyncMock(side_effect=RuntimeError("db is down")),
    )

    final_state = await run_support_workflow("cust-1", "Does Pro include API access?")

    assert final_state["final_response"]
    assert not final_state["escalation_required"]
    assert not final_state["human_approval_required"]
