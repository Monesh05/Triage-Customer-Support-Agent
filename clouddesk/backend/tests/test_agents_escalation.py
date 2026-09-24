# tests/test_agents_escalation.py
# Purpose: Unit tests for the Escalation Agent (app.agents.escalation). Mocks the LLM client
#          layer. Covers the happy path (a structured internal handoff, per spec section 17)
#          and malformed-output handling.
# Author: CloudDesk Team
# Date: 2026-09-24

import pytest

from app.agents.escalation import run_escalation_agent
from app.agents.schemas import EscalationAgentResult
from app.llm.structured import AgentError
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage


async def test_escalation_agent_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """A structured internal handoff is produced, never a bare 'contact support' message."""
    fake_llm = FakeLLM()
    expected = EscalationAgentResult(
        customer="cust-1",
        issue="Duplicate charge and API access issue; customer requested a human.",
        intent=["billing", "technical"],
        priority="urgent",
        investigation_performed=["Checked payment history.", "Checked API key status."],
        evidence=["PAY_123", "PAY_124"],
        actions_attempted=["Refund request created (pending approval)."],
        unresolved_questions=["Was the entitlement refresh confirmed by the customer?"],
        recommended_human_action="Approve the refund and verify entitlement sync manually.",
        conversation_history=["Customer: I was charged twice and want a human."],
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=expected)
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_escalation_agent(
        customer_id="cust-1",
        customer_message="I was charged twice and want a human.",
        triage={"priority": "urgent", "required_agents": ["billing", "technical"]},
        specialist_results={"billing": {"status": "resolved"}},
    )

    assert isinstance(result, EscalationAgentResult)
    assert result.recommended_human_action
    assert "contact support" not in result.recommended_human_action.lower()


async def test_escalation_agent_handles_malformed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model reply that never yields valid JSON returns AgentError, not a crash."""
    fake_llm = FakeLLM()
    fake_llm.client.beta.chat.completions.parse.side_effect = Exception("no schema support")
    fake_llm.client.chat.completions.create.return_value = FakeCompletion(
        FakeMessage(content="garbage")
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_escalation_agent(
        customer_id="cust-1", customer_message="test", triage={}, specialist_results={}
    )

    assert isinstance(result, AgentError)
    assert result.agent == "escalation"
