# tests/test_agents_billing.py
# Purpose: Unit tests for the Billing Agent (app.agents.billing). Mocks the LLM client layer AND
#          the underlying Phase 2 billing tool functions, so no real API/DB call is made. Covers
#          the happy path, malformed-output handling, the exact allowed-tool set (spec section
#          10), and that the bounded tool-call loop respects MAX_TOOL_CALL_ROUNDS.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
from unittest.mock import AsyncMock

import pytest

from app.agents.base import MAX_TOOL_CALL_ROUNDS
from app.agents.billing import _build_tools, run_billing_agent
from app.agents.schemas import BillingAgentResult, Finding, RecommendedAction
from app.llm.structured import AgentError
from app.tools.base import ToolResult
from tests._llm_fakes import FakeCompletion, FakeLLM, FakeMessage, FakeToolCall


def test_billing_agent_tool_allowlist() -> None:
    """Spec section 10: the Billing Agent may only call these exact six tools."""
    names = {spec.name for spec in _build_tools()}
    assert names == {
        "get_subscription",
        "get_payment_history",
        "get_invoice",
        "calculate_refund",
        "get_billing_policy",
        "create_refund_request",
    }


async def test_billing_agent_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """The agent calls an allowed tool, then produces a structured BillingAgentResult."""
    fake_llm = FakeLLM()
    tool_call = FakeToolCall("call_1", "get_payment_history", json.dumps({"customer_id": "cust-1"}))
    fake_llm.client.chat.completions.create.side_effect = [
        FakeCompletion(FakeMessage(tool_calls=[tool_call])),
        FakeCompletion(FakeMessage(content=None, tool_calls=None)),
    ]
    expected = BillingAgentResult(
        status="resolved",
        findings=[Finding(fact="Two successful payments of $49 exist for the same period.")],
        recommended_actions=[RecommendedAction(action="refund", amount=49, requires_approval=True)],
        evidence=["PAY_123", "PAY_124"],
    )
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(parsed=expected)
    )
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    fake_history = AsyncMock(return_value=ToolResult(success=True, data=[]))
    monkeypatch.setattr("app.agents.billing.billing_tools.get_payment_history", fake_history)

    result = await run_billing_agent("cust-1", "I was charged twice.")

    assert isinstance(result, BillingAgentResult)
    assert result.evidence == ["PAY_123", "PAY_124"]
    fake_history.assert_awaited_once_with("cust-1")


async def test_billing_agent_handles_malformed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the model never calls a tool and the final output can't be parsed, return AgentError."""
    fake_llm = FakeLLM()
    fake_llm.client.chat.completions.create.side_effect = [
        FakeCompletion(FakeMessage(content=None, tool_calls=None)),
        FakeCompletion(FakeMessage(content="not json")),
        FakeCompletion(FakeMessage(content="still not json")),
    ]
    fake_llm.client.beta.chat.completions.parse.side_effect = Exception("no schema support")
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)

    result = await run_billing_agent("cust-1", "I was charged twice.")

    assert isinstance(result, AgentError)
    assert result.agent == "billing"


async def test_billing_agent_tool_loop_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the model keeps requesting tools forever, the loop stops after MAX_TOOL_CALL_ROUNDS."""
    fake_llm = FakeLLM()

    def _always_call_tool(*_args: object, **_kwargs: object) -> FakeCompletion:
        call = FakeToolCall("call_x", "get_subscription", json.dumps({"customer_id": "cust-1"}))
        return FakeCompletion(FakeMessage(tool_calls=[call]))

    fake_llm.client.chat.completions.create.side_effect = _always_call_tool
    fake_llm.client.beta.chat.completions.parse.return_value = FakeCompletion(
        FakeMessage(
            parsed=BillingAgentResult(
                status="unresolved", findings=[], recommended_actions=[], evidence=[]
            )
        )
    )
    monkeypatch.setattr("app.agents.base.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr("app.llm.structured.get_llm_client", lambda: fake_llm)
    monkeypatch.setattr(
        "app.agents.billing.billing_tools.get_subscription",
        AsyncMock(return_value=ToolResult(success=True, data=[])),
    )

    result = await run_billing_agent("cust-1", "loop forever please")

    assert isinstance(result, BillingAgentResult)
    assert fake_llm.client.chat.completions.create.await_count == MAX_TOOL_CALL_ROUNDS
