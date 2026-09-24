# tests/test_agents_qa.py
# Purpose: Unit tests for the QA/Critic Agent (app.agents.qa). Mocks the LLM client layer.
#          Covers the "rejected" example from spec section 16 (a draft that overclaims an
#          action happened) and malformed-output handling.
# Author: CloudDesk Team
# Date: 2026-09-24

import pytest

from app.agents.qa import run_qa_agent
from app.agents.schemas import QAAgentResult
from app.llm.structured import AgentError
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage


async def test_qa_agent_rejects_overclaiming_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spec section 16 example: a draft claiming a refund was processed (only requested) fails."""
    fake_llm = FakeLLM()
    expected = QAAgentResult(
        approved=False,
        issues=["The response says the refund was processed, but only a request was created."],
        required_changes=["State that the refund request was created and is pending approval."],
        evidence_supported=False,
        hallucination_detected=False,
        policy_compliant=True,
        actions_confirmed=False,
        escalation_needed=False,
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=expected)
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    specialist_results = {"billing": {"status": "resolved", "evidence": ["PAY_123"]}}
    resolution = {"customer_facing_draft": "We have refunded your duplicate payment."}
    result = await run_qa_agent("I was charged twice.", specialist_results, resolution)

    assert isinstance(result, QAAgentResult)
    assert result.approved is False
    assert result.actions_confirmed is False


async def test_qa_agent_final_attempt_notice_reaches_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """is_final_attempt=True must add the FINAL ATTEMPT notice to the reviewed material."""
    fake_llm = FakeLLM()
    approved = QAAgentResult(
        approved=True,
        issues=[],
        required_changes=[],
        evidence_supported=True,
        hallucination_detected=False,
        policy_compliant=True,
        actions_confirmed=True,
        escalation_needed=False,
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=approved)
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_qa_agent("I was charged twice.", {}, {}, is_final_attempt=True)

    assert isinstance(result, QAAgentResult)
    assert result.approved is True
    _, kwargs = fake_llm.client.beta.chat.completions.parse.call_args
    user_message = next(m["content"] for m in kwargs["messages"] if m["role"] == "user")
    assert "FINAL review" in user_message


async def test_qa_agent_handles_malformed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model reply that never yields valid JSON returns AgentError, not a crash."""
    fake_llm = FakeLLM()
    fake_llm.client.beta.chat.completions.parse.side_effect = Exception("no schema support")
    fake_llm.client.chat.completions.create.return_value = FakeCompletion(
        FakeMessage(content="garbage")
    )
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_qa_agent("test", {}, {})

    assert isinstance(result, AgentError)
    assert result.agent == "qa"
