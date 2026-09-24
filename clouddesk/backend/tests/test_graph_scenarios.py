# tests/test_graph_scenarios.py
# Purpose: End-to-end (mocked) tests of the compiled support StateGraph against the spec section
#          23 example scenarios (A-G). Every `app.agents.*` entrypoint is monkeypatched to a
#          canned result/AgentError so no real LLM call is made (same policy as Phase 3's
#          default suite) — these tests exercise the GRAPH's routing/fan-out/state logic only.
# Author: CloudDesk Team
# Date: 2026-09-24

from unittest.mock import AsyncMock

import pytest

from app.agents.schemas import (
    AccountAgentResult,
    BillingAgentResult,
    ProductAgentResult,
    RecommendedAction,
    TechnicalAgentResult,
    TriageResult,
)
from app.graph.graph import run_support_workflow
from app.llm.structured import AgentError


def _triage(**overrides: object) -> TriageResult:
    defaults: dict[str, object] = {
        "intents": ["other"],
        "priority": "medium",
        "sentiment": "neutral",
        "required_agents": [],
        "reason": "test",
    }
    defaults.update(overrides)
    return TriageResult.model_validate(defaults)


def _billing(requires_approval: bool = False) -> BillingAgentResult:
    return BillingAgentResult(
        status="resolved",
        findings=[{"fact": "Two payments found."}],
        recommended_actions=[
            RecommendedAction(action="refund", amount=49, requires_approval=requires_approval)
        ],
        evidence=["PAY_1", "PAY_2"],
    )


def _account() -> AccountAgentResult:
    return AccountAgentResult(
        status="resolved", findings=[{"fact": "Account is locked."}], recommended_actions=[], evidence=["ACC_1"]
    )


def _technical(status: str = "resolved") -> TechnicalAgentResult:
    return TechnicalAgentResult(
        hypothesis="Entitlement mismatch causes 403.", status=status, evidence=["INC_1"], recommended_actions=[]
    )


def _product() -> ProductAgentResult:
    return ProductAgentResult(
        answer="Pro includes API access.",
        sources=[{"document_id": "pricing-plans", "title": "CloudDesk Pricing Plans", "category": "pricing"}],
        grounded=True,
    )


def _resolution_result(requires_approval: bool = False) -> dict[str, object]:
    return {
        "summary": "Synthesis.",
        "issues_identified": [],
        "proposed_resolution": "Do the thing.",
        "customer_facing_draft": "Here is your answer.",
        "unresolved_questions": [],
        "requires_approval": requires_approval,
    }


def _qa_result(approved: bool = True) -> dict[str, object]:
    return {
        "approved": approved,
        "issues": [] if approved else ["needs work"],
        "required_changes": [] if approved else ["fix it"],
        "evidence_supported": True,
        "hallucination_detected": False,
        "policy_compliant": True,
        "actions_confirmed": True,
        "escalation_needed": False,
    }


async def test_scenario_a_simple_faq_routes_only_to_product(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(return_value=_triage(intents=["product"], required_agents=["product"])),
    )
    product_mock = AsyncMock(return_value=_product())
    monkeypatch.setattr("app.graph.nodes.run_product_agent", product_mock)
    billing_mock = AsyncMock()
    monkeypatch.setattr("app.graph.nodes.run_billing_agent", billing_mock)

    from app.agents.schemas import ResolutionAgentResult

    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_resolution_agent",
        AsyncMock(return_value=ResolutionAgentResult.model_validate(_resolution_result())),
    )
    from app.agents.schemas import QAAgentResult

    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=QAAgentResult.model_validate(_qa_result(True)))
    )

    final_state = await run_support_workflow("cust-1", "Does Pro include API access?")

    product_mock.assert_awaited_once()
    billing_mock.assert_not_awaited()
    assert "product" in final_state["specialist_results"]
    assert "billing" not in final_state["specialist_results"]
    assert final_state["final_response"]
    assert not final_state["human_approval_required"]
    assert not final_state["escalation_required"]


async def test_scenario_b_duplicate_payment_requires_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.schemas import QAAgentResult, ResolutionAgentResult

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(return_value=_triage(intents=["billing"], required_agents=["billing"])),
    )
    monkeypatch.setattr("app.graph.nodes.run_billing_agent", AsyncMock(return_value=_billing(requires_approval=True)))
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_resolution_agent",
        AsyncMock(return_value=ResolutionAgentResult.model_validate(_resolution_result(True))),
    )
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=QAAgentResult.model_validate(_qa_result(True)))
    )

    final_state = await run_support_workflow("cust-1", "Why was I charged twice?")

    assert final_state["human_approval_required"] is True
    assert final_state["pending_actions"]
    assert final_state["pending_actions"][0]["agent"] == "billing"


async def test_scenario_c_account_lockout_routes_only_to_account(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.schemas import QAAgentResult, ResolutionAgentResult

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(return_value=_triage(intents=["account"], required_agents=["account"])),
    )
    account_mock = AsyncMock(return_value=_account())
    monkeypatch.setattr("app.graph.nodes.run_account_agent", account_mock)
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_resolution_agent",
        AsyncMock(return_value=ResolutionAgentResult.model_validate(_resolution_result())),
    )
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=QAAgentResult.model_validate(_qa_result(True)))
    )

    final_state = await run_support_workflow("cust-1", "I can't log into my account.")

    account_mock.assert_awaited_once()
    assert set(final_state["specialist_results"]) == {"account"}


async def test_scenario_d_api_failure_runs_technical_and_account_in_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.schemas import QAAgentResult, ResolutionAgentResult

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(
            return_value=_triage(intents=["technical", "account"], required_agents=["technical", "account"])
        ),
    )
    technical_mock = AsyncMock(return_value=_technical())
    account_mock = AsyncMock(return_value=_account())
    monkeypatch.setattr("app.graph.nodes.run_technical_agent", technical_mock)
    monkeypatch.setattr("app.graph.nodes.run_account_agent", account_mock)
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_resolution_agent",
        AsyncMock(return_value=ResolutionAgentResult.model_validate(_resolution_result())),
    )
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=QAAgentResult.model_validate(_qa_result(True)))
    )

    final_state = await run_support_workflow("cust-1", "My API returns 403.")

    technical_mock.assert_awaited_once()
    account_mock.assert_awaited_once()
    assert set(final_state["specialist_results"]) == {"technical", "account"}


async def test_scenario_e_multi_intent_runs_all_three_specialists_in_parallel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.schemas import QAAgentResult, ResolutionAgentResult

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(
            return_value=_triage(
                intents=["billing", "account", "technical"],
                required_agents=["billing", "account", "technical"],
            )
        ),
    )
    billing_mock = AsyncMock(return_value=_billing())
    account_mock = AsyncMock(return_value=_account())
    technical_mock = AsyncMock(return_value=_technical())
    monkeypatch.setattr("app.graph.nodes.run_billing_agent", billing_mock)
    monkeypatch.setattr("app.graph.nodes.run_account_agent", account_mock)
    monkeypatch.setattr("app.graph.nodes.run_technical_agent", technical_mock)
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_resolution_agent",
        AsyncMock(return_value=ResolutionAgentResult.model_validate(_resolution_result())),
    )
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=QAAgentResult.model_validate(_qa_result(True)))
    )

    final_state = await run_support_workflow("cust-1", "Upgraded, charged twice, API broken.")

    billing_mock.assert_awaited_once()
    account_mock.assert_awaited_once()
    technical_mock.assert_awaited_once()
    assert set(final_state["specialist_results"]) == {"billing", "account", "technical"}


async def test_scenario_f_active_outage_follows_required_agents_faithfully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.schemas import QAAgentResult, ResolutionAgentResult

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(return_value=_triage(intents=["technical"], required_agents=["technical"])),
    )
    technical_mock = AsyncMock(return_value=_technical(status="resolved"))
    account_mock = AsyncMock()
    monkeypatch.setattr("app.graph.nodes.run_technical_agent", technical_mock)
    monkeypatch.setattr("app.graph.nodes.run_account_agent", account_mock)
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_resolution_agent",
        AsyncMock(return_value=ResolutionAgentResult.model_validate(_resolution_result())),
    )
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=QAAgentResult.model_validate(_qa_result(True)))
    )

    final_state = await run_support_workflow("cust-1", "My API is failing.")

    technical_mock.assert_awaited_once()
    account_mock.assert_not_awaited()
    assert set(final_state["specialist_results"]) == {"technical"}


async def test_scenario_g_explicit_human_request_skips_specialists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(return_value=_triage(intents=["other"], required_agents=["escalation"])),
    )
    billing_mock = AsyncMock()
    monkeypatch.setattr("app.graph.nodes.run_billing_agent", billing_mock)
    from app.agents.schemas import EscalationAgentResult

    escalation_mock = AsyncMock(
        return_value=EscalationAgentResult(
            customer="cust-1",
            issue="Wants a human.",
            intent=["other"],
            priority="medium",
            investigation_performed=[],
            evidence=[],
            actions_attempted=[],
            unresolved_questions=[],
            recommended_human_action="Route to a live agent immediately.",
            conversation_history=[],
        )
    )
    monkeypatch.setattr("app.graph.resolution_nodes.run_escalation_agent", escalation_mock)

    final_state = await run_support_workflow("cust-1", "I want to speak to a human.")

    escalation_mock.assert_awaited_once()
    billing_mock.assert_not_awaited()
    assert final_state["escalation_required"] is True
    assert final_state["specialist_results"] == {}
    assert final_state["final_response"]
    assert "contact support" not in final_state["final_response"].lower()


async def test_specialist_agent_error_does_not_crash_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.schemas import QAAgentResult, ResolutionAgentResult

    monkeypatch.setattr(
        "app.graph.nodes.run_triage_agent",
        AsyncMock(return_value=_triage(intents=["billing"], required_agents=["billing"])),
    )
    monkeypatch.setattr(
        "app.graph.nodes.run_billing_agent",
        AsyncMock(return_value=AgentError(agent="billing", message="LLM timed out")),
    )
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_resolution_agent",
        AsyncMock(return_value=ResolutionAgentResult.model_validate(_resolution_result())),
    )
    monkeypatch.setattr(
        "app.graph.resolution_nodes.run_qa_agent", AsyncMock(return_value=QAAgentResult.model_validate(_qa_result(True)))
    )

    final_state = await run_support_workflow("cust-1", "I was charged twice.")

    assert any("billing" in error for error in final_state["errors"])
    assert final_state["specialist_results"]["billing"]["error"] == "LLM timed out"
    assert final_state["final_response"]
